"""
udgs_core test suite — QA8 grade
Covers: anchors, state_machine, strict_json, system_object, autonomous_audit, cli, adapter
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Any, Dict

import pytest

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ═══════════════════════════════════════════════════════════════════════
# ANCHORS
# ═══════════════════════════════════════════════════════════════════════

from udgs_core.anchors import sha256_bytes, sha256_file, sha256_json, sha256_tree


class TestSha256Bytes:
    def test_known_vector_empty(self):
        assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_known_vector_abc(self):
        # SHA-256("abc") — Python hashlib verified
        assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    def test_length_always_64(self):
        for n in range(0, 300, 37):
            assert len(sha256_bytes(bytes(n))) == 64

    def test_deterministic(self):
        data = b"test payload 123"
        assert sha256_bytes(data) == sha256_bytes(data)

    def test_avalanche(self):
        msg = b"axl udgs payload"
        msg2 = msg[:-1] + bytes([msg[-1] ^ 0x01])
        assert sha256_bytes(msg) != sha256_bytes(msg2)
        diffs = sum(a != b for a, b in zip(sha256_bytes(msg), sha256_bytes(msg2)))
        assert diffs > 20


class TestSha256Json:
    def test_key_order_invariant(self):
        a = {"z": 1, "a": 2, "m": {"b": 3}}
        b = {"a": 2, "m": {"b": 3}, "z": 1}
        assert sha256_json(a) == sha256_json(b)

    def test_different_values_differ(self):
        assert sha256_json({"x": 1}) != sha256_json({"x": 2})

    def test_list_order_matters(self):
        assert sha256_json({"a": [1, 2]}) != sha256_json({"a": [2, 1]})

    def test_deep_nesting(self):
        obj: Dict[str, Any] = {}
        cur = obj
        for i in range(150):
            cur["n"] = {"level": i}
            cur = cur["n"]
        h = sha256_json(obj)
        assert len(h) == 64

    def test_collision_resistant(self):
        pairs = [
            ({"a": 1}, {"b": 1}),
            ({"": "x"}, {"x": ""}),
            ({"a": None}, {"a": False}),
        ]
        for o1, o2 in pairs:
            assert sha256_json(o1) != sha256_json(o2), f"Collision: {o1}"


class TestSha256File:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        h1 = sha256_file(str(f))
        h2 = sha256_file(str(f))
        assert h1 == h2
        assert len(h1) == 64

    def test_content_sensitivity(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_bytes(b"content_a")
        g = tmp_path / "b.txt"
        g.write_bytes(b"content_b")
        assert sha256_file(str(f)) != sha256_file(str(g))


class TestSha256Tree:
    def test_empty_dir_deterministic(self, tmp_path):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir(); d2.mkdir()
        h1, _ = sha256_tree(str(d1))
        h2, _ = sha256_tree(str(d2))
        assert h1 == h2

    def test_idempotent_10x(self):
        hashes = [sha256_tree(os.path.join(ROOT, "engine"))[0] for _ in range(10)]
        assert len(set(hashes)) == 1

    def test_file_change_detected(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("original")
        h1, _ = sha256_tree(str(tmp_path))
        f.write_text("modified")
        h2, _ = sha256_tree(str(tmp_path))
        assert h1 != h2

    def test_exclude_rel_paths(self, tmp_path):
        (tmp_path / "include.txt").write_text("include")
        (tmp_path / "exclude.txt").write_text("exclude")
        h_with, _ = sha256_tree(str(tmp_path))
        h_without, _ = sha256_tree(str(tmp_path), exclude_rel_paths={"exclude.txt"})
        assert h_with != h_without

    def test_returns_file_hashes_dict(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        _, files = sha256_tree(str(tmp_path))
        assert "a.txt" in files
        assert "b.txt" in files

    def test_path_traversal_normalized(self, tmp_path):
        (tmp_path / "file.txt").write_text("content")
        h1, _ = sha256_tree(str(tmp_path))
        h2, _ = sha256_tree(str(tmp_path / ".." / tmp_path.name))
        assert h1 == h2


# ═══════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════

from udgs_core.state_machine import DeterministicCycle, Evidence, LoopState


class TestDeterministicCycle:
    def _good_ev(self):
        return Evidence(logs={"x": 1}, hash_anchor="abc", oracle_pass=True)

    def test_nominal_four_steps(self):
        c = DeterministicCycle(fail_closed=True)
        ev = self._good_ev()
        assert c.step(ev).next_state == LoopState.FIX
        assert c.step(ev).next_state == LoopState.PROVE
        assert c.step(ev).next_state == LoopState.CHECKPOINT
        assert c.step(ev).next_state == LoopState.FAIL  # wraps

    def test_halt_on_missing_logs(self):
        c = DeterministicCycle(fail_closed=True)
        ev = Evidence(logs=None, hash_anchor="abc", oracle_pass=True)
        c.step(ev); c.step(ev)
        r = c.step(ev)
        assert r.next_state == LoopState.HALT

    def test_halt_on_missing_anchor(self):
        c = DeterministicCycle(fail_closed=True)
        ev = Evidence(logs={"x": 1}, hash_anchor=None)
        c.step(ev); c.step(ev)
        assert c.step(ev).next_state == LoopState.HALT

    def test_halt_on_oracle_false(self):
        c = DeterministicCycle(fail_closed=True)
        ev = Evidence(logs={"x": 1}, hash_anchor="abc", oracle_pass=False)
        c.step(ev); c.step(ev)
        assert c.step(ev).next_state == LoopState.HALT

    def test_halt_is_absorbing(self):
        c = DeterministicCycle(fail_closed=True)
        ev_bad = Evidence()
        for _ in range(3):
            c.step(ev_bad)
        for _ in range(30):
            r = c.step(self._good_ev())
            assert r.next_state == LoopState.HALT

    def test_history_completeness(self):
        c = DeterministicCycle()
        ev = self._good_ev()
        for _ in range(8):
            c.step(ev)
        assert len(c.history) == 8

    def test_violated_invariants_populated(self):
        c = DeterministicCycle(fail_closed=True)
        ev_bad = Evidence(logs=None, hash_anchor=None)
        c.step(ev_bad); c.step(ev_bad)
        r = c.step(ev_bad)
        assert len(r.violated) >= 2

    def test_notes_nonempty(self):
        c = DeterministicCycle()
        ev = self._good_ev()
        r = c.step(ev)
        assert len(r.notes) > 0


# ═══════════════════════════════════════════════════════════════════════
# STRICT JSON
# ═══════════════════════════════════════════════════════════════════════

from udgs_core.strict_json import compute_packet_anchor, validate_packet


def _valid_packet(**overrides) -> Dict[str, Any]:
    p: Dict[str, Any] = {
        "FAIL_PACKET": {"summary": "test summary", "signals": ["sig1"], "repro": "pytest"},
        "MUTATION_PLAN": {"diff_scope": ["module.py"], "constraints": ["fail-closed"]},
        "PRE_VERIFICATION_SCRIPT": "python -m pytest",
        "REGRESSION_TEST_PAYLOAD": {"suite": ["test_a"], "expected": {"pass": True}},
        "SHA256_ANCHOR": "REPLACE",
    }
    p.update(overrides)
    p["SHA256_ANCHOR"] = compute_packet_anchor(p)
    return p


class TestValidatePacket:
    def test_valid_packet_ok(self):
        ok, errs = validate_packet(_valid_packet())
        assert ok, str(errs)

    def test_missing_top_level_key_fails(self):
        p = _valid_packet()
        del p["MUTATION_PLAN"]
        ok, _ = validate_packet(p)
        assert not ok

    def test_extra_top_level_key_rejected(self):
        p = _valid_packet()
        p["EXTRA"] = "bad"
        p["SHA256_ANCHOR"] = compute_packet_anchor(p)
        # extra key still fails
        ok, _ = validate_packet(p)
        assert not ok

    def test_anchor_mismatch_rejected(self):
        p = _valid_packet()
        p["SHA256_ANCHOR"] = "a" * 64
        ok, errs = validate_packet(p)
        assert not ok
        assert any("Anchor mismatch" in e.message for e in errs)

    def test_uppercase_anchor_rejected(self):
        p = _valid_packet()
        p["SHA256_ANCHOR"] = "A" * 64
        ok, _ = validate_packet(p)
        assert not ok

    def test_empty_signals_rejected(self):
        p = _valid_packet()
        p["FAIL_PACKET"]["signals"] = []
        ok, _ = validate_packet(p)
        assert not ok

    def test_empty_summary_rejected(self):
        p = _valid_packet()
        p["FAIL_PACKET"]["summary"] = "   "
        ok, _ = validate_packet(p)
        assert not ok

    def test_empty_expected_rejected(self):
        p = _valid_packet()
        p["REGRESSION_TEST_PAYLOAD"]["expected"] = {}
        ok, _ = validate_packet(p)
        assert not ok

    def test_anchor_self_consistent_after_roundtrip(self):
        p = _valid_packet()
        anchor = compute_packet_anchor(p)
        assert p["SHA256_ANCHOR"] == anchor

    def test_large_packet_accepted(self):
        p = _valid_packet()
        p["REGRESSION_TEST_PAYLOAD"]["suite"] = [f"test_{i}" for i in range(500)]
        p["REGRESSION_TEST_PAYLOAD"]["expected"] = {str(i): True for i in range(100)}
        p["SHA256_ANCHOR"] = compute_packet_anchor(p)
        ok, errs = validate_packet(p)
        assert ok, str(errs)


# ═══════════════════════════════════════════════════════════════════════
# ADAPTER
# ═══════════════════════════════════════════════════════════════════════

from udgs_core.adapters.dao_lifebook_adapter import proof_bundle_to_udgs_packet


class TestDaoLifebookAdapter:
    def _bundle(self, status="success"):
        return {
            "required_checks_status": status,
            "commit_sha": "abc123def456",
            "artifact_hashes": {"engine": "deadbeef" * 8},
        }

    def test_produces_valid_packet_success(self):
        pkt = proof_bundle_to_udgs_packet(self._bundle("success"), pre_verification_script="make check")
        ok, errs = validate_packet(pkt)
        assert ok, str(errs)

    @pytest.mark.parametrize("status", ["success", "failure", "pending", "skipped"])
    def test_all_valid_statuses_produce_valid_packets(self, status):
        pkt = proof_bundle_to_udgs_packet(self._bundle(status), pre_verification_script="run")
        ok, errs = validate_packet(pkt)
        assert ok, f"status={status}: {errs}"

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            proof_bundle_to_udgs_packet(self._bundle("INVALID"), pre_verification_script="r")

    def test_missing_required_key_raises(self):
        bundle = {"commit_sha": "abc", "artifact_hashes": {}}
        with pytest.raises(ValueError, match="Missing key"):
            proof_bundle_to_udgs_packet(bundle, pre_verification_script="r")

    def test_anchor_is_valid_sha256(self):
        import re
        pkt = proof_bundle_to_udgs_packet(self._bundle(), pre_verification_script="r")
        assert re.match(r"^[a-f0-9]{64}$", pkt["SHA256_ANCHOR"])

    def test_packet_has_required_regression_keys(self):
        pkt = proof_bundle_to_udgs_packet(self._bundle(), pre_verification_script="r")
        rp = pkt["REGRESSION_TEST_PAYLOAD"]
        assert "suite" in rp and len(rp["suite"]) > 0
        assert "expected" in rp and len(rp["expected"]) > 0


# ═══════════════════════════════════════════════════════════════════════
# AUTONOMOUS AUDIT
# ═══════════════════════════════════════════════════════════════════════

from udgs_core.autonomous_audit import (
    AutonomousAuditEngine,
    ComponentDrift,
    Qa8Mode,
    QA8_GRADE,
    score_system,
)


def _make_test_engine(tmp_path):
    """Build a minimal but real engine for testing."""
    from udgs_core.anchors import sha256_tree, sha256_file
    from udgs_core.system_object import sha256_tree_payload

    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    (engine_dir / "stub.py").write_text("# stub")

    config = {
        "audit_exclude_rel_paths": [],
        "audit_exclude_rel_prefixes": ["qa8_state/"],
    }
    config_path = tmp_path / "udgs.config.json"
    config_path.write_text(json.dumps(config))

    engine_hash, _ = sha256_tree(str(engine_dir))
    config_hash = sha256_file(str(config_path))
    anchor_payload = {"config_hash": config_hash, "components": {"AXL_ENGINE": engine_hash}}
    system_anchor = sha256_tree_payload(anchor_payload)

    so = {
        "config": config,
        "components": {
            "AXL_ENGINE": {"name": "AXL_ENGINE", "path": "engine", "kind": "engine", "hash": engine_hash}
        },
        "system_anchor": system_anchor,
        "audit": {"excluded_from_root_hash": [], "excluded_prefixes_from_root_hash": ["qa8_state/"]},
    }
    so_path = tmp_path / "SYSTEM_OBJECT.json"
    so_path.write_text(json.dumps(so, indent=2))
    (tmp_path / "qa8_state").mkdir()

    eng = AutonomousAuditEngine(
        root=str(tmp_path),
        config_path=str(config_path),
        system_object_path=str(so_path),
        qa8_state_dir=str(tmp_path / "qa8_state"),
        qa8_config={},
    )
    return eng


class TestAutonomousAuditEngine:
    def test_nominal_no_drift(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        status = eng.run_cycle()
        assert status.mode == Qa8Mode.NOMINAL
        assert status.baseline_anchor == status.live_anchor

    def test_grade_is_qa8(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        status = eng.run_cycle()
        assert status.grade == QA8_GRADE

    def test_source_drift_triggers_alert(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        (tmp_path / "engine" / "injected.py").write_text("# drift")
        status = eng.run_cycle()
        assert status.mode in (Qa8Mode.ALERT, Qa8Mode.HEALED)

    def test_status_file_written(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        eng.run_cycle()
        assert (tmp_path / "qa8_state" / "QA8_STATUS.json").exists()

    def test_heal_log_written_on_drift(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        (tmp_path / "engine" / "drift.txt").write_text("drift")
        eng.run_cycle()
        log = tmp_path / "qa8_state" / "HEAL_LOG.jsonl"
        assert log.exists()
        lines = log.read_text().strip().splitlines()
        assert len(lines) > 0
        event = json.loads(lines[-1])
        assert all(k in event for k in ("event_id", "drifts", "outcome", "utc"))

    def test_scan_count_increments(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        for i in range(1, 6):
            status = eng.run_cycle()
            assert status.scan_count == i

    def test_missing_component_reported_as_drift(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        # Manually insert ghost component in baseline
        baseline = eng._baseline
        baseline["components"]["GHOST"] = {"name": "GHOST", "path": "nonexistent", "kind": "engine", "hash": "x" * 64}
        drifts = eng.detect_drift()
        ghost_drifts = [d for d in drifts if d.name == "GHOST"]
        assert len(ghost_drifts) == 1
        assert ghost_drifts[0].live_hash == "MISSING"

    def test_watch_terminates_on_max_cycles(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        eng.watch(interval_sec=0.0, max_cycles=5)
        status_data = json.loads((tmp_path / "qa8_state" / "QA8_STATUS.json").read_text())
        assert status_data["scan_count"] == 5

    def test_auto_loads_baseline_in_run_cycle(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        # Do NOT call load_baseline()
        status = eng.run_cycle()  # must auto-load
        assert status.mode == Qa8Mode.NOMINAL

    def test_status_schema_complete(self, tmp_path):
        eng = _make_test_engine(tmp_path)
        eng.load_baseline()
        status = eng.run_cycle()
        d = status.as_dict()
        for key in ("mode", "last_scan_utc", "scan_count", "heal_count",
                    "alert_count", "halt_count", "baseline_anchor", "live_anchor", "grade"):
            assert key in d, f"Missing key: {key}"


class TestScoreSystem:
    def test_perfect_score(self):
        baseline = {"components": {"A": {"hash": "aaa"}, "B": {"hash": "bbb"}}}
        result = score_system(baseline, {"A": "aaa", "B": "bbb"})
        assert result["integrity_score"] == 1.0
        assert result["grade"] == "PASS"
        assert result["drifted"] == 0

    def test_degraded_score(self):
        baseline = {"components": {f"C{i}": {"hash": f"h{i}"} for i in range(4)}}
        live = {f"C{i}": ("CHANGED" if i < 2 else f"h{i}") for i in range(4)}
        result = score_system(baseline, live)
        assert result["grade"] == "DEGRADED"
        assert result["drifted"] == 2
        assert abs(result["integrity_score"] - 0.5) < 0.001

    def test_empty_baseline_perfect(self):
        result = score_system({"components": {}}, {})
        assert result["integrity_score"] == 1.0

    def test_thread_safety(self):
        baseline = {"components": {f"C{i}": {"hash": f"h{i}"} for i in range(30)}}
        live = {f"C{i}": f"h{i}" for i in range(30)}
        results = []
        def run():
            results.append(score_system(baseline, live)["integrity_score"])
        threads = [threading.Thread(target=run) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(s == 1.0 for s in results)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

class TestCLI:
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "udgs_core.cli"] + list(args),
            capture_output=True, text=True, cwd=ROOT
        )

    def test_anchor_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello")
        r = self._run("anchor", str(f))
        assert r.returncode == 0
        assert len(r.stdout.strip()) == 64

    def test_anchor_dir(self):
        r = self._run("anchor", "engine")
        assert r.returncode == 0
        assert len(r.stdout.strip()) == 64

    def test_validate_packet_valid(self):
        r = self._run("validate-packet", "system/examples/packet.example.json")
        assert r.returncode == 0
        assert r.stdout.strip() == "OK"

    def test_validate_packet_invalid_anchor(self):
        r = self._run("validate-packet", "system/examples/packet.invalid.anchor_mismatch.json")
        assert r.returncode != 0

    def test_validate_packet_invalid_extra_key(self):
        r = self._run("validate-packet", "system/examples/packet.invalid.extra_key.json")
        assert r.returncode != 0

    def test_build_system_object(self, tmp_path):
        out = tmp_path / "SO.json"
        r = self._run("build-system-object", "--root", ROOT,
                      "--config", os.path.join(ROOT, "system/udgs.config.json"),
                      "--out", str(out))
        assert r.returncode == 0
        assert len(r.stdout.strip()) == 64  # prints system_anchor
        so = json.loads(out.read_text())
        assert "system_anchor" in so
        assert "components" in so

    def test_build_system_object_deterministic(self, tmp_path):
        out1 = tmp_path / "SO1.json"
        out2 = tmp_path / "SO2.json"
        r1 = self._run("build-system-object", "--root", ROOT,
                       "--config", os.path.join(ROOT, "system/udgs.config.json"),
                       "--out", str(out1))
        r2 = self._run("build-system-object", "--root", ROOT,
                       "--config", os.path.join(ROOT, "system/udgs.config.json"),
                       "--out", str(out2))
        assert r1.stdout.strip() == r2.stdout.strip()

    def test_qa8_heal_nominal(self):
        # rebuild system object first so it's consistent
        self._run("build-system-object", "--root", ROOT,
                  "--config", os.path.join(ROOT, "system/udgs.config.json"),
                  "--out", os.path.join(ROOT, "SYSTEM_OBJECT.json"))
        r = self._run("qa8-heal", "--root", ROOT)
        assert r.returncode == 0
        result = json.loads(r.stdout)
        assert result["mode"] == "NOMINAL"
        assert result["grade"].startswith("QA8")

    def test_qa8_status_file_readable(self):
        r = self._run("qa8-status", "--root", ROOT)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "mode" in data and "grade" in data

    def test_loop_nominal(self, tmp_path):
        ev = tmp_path / "evidence.json"
        ev.write_text(json.dumps({"logs": {"x": 1}, "hash_anchor": "abc", "oracle_pass": True}))
        r = self._run("loop", "--evidence-json", str(ev))
        assert r.returncode == 0
        result = json.loads(r.stdout)
        assert result["next_state"] == "CHECKPOINT"

    def test_loop_halt_on_no_evidence(self):
        r = self._run("loop")
        assert r.returncode != 0
        result = json.loads(r.stdout)
        assert result["next_state"] == "HALT"
