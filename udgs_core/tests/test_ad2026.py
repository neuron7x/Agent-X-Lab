"""
udgs_core.tests.test_ad2026
============================
AD-2026 ABSOLUTE_DETERMINISM_2026 — complete test suite

Covers:
  L0 identity  : AAID, ACRootKey, JWS, APBChain, ZTO
  L1 typed_plan: TypedAction, SPS, InvariantSet, SMTGate, SPSValidator
  Gates G6–G11 : all fail-closed paths
  L4 cognitive : CIL9Metrics, BSSPlanner determinism, CRSMBoundary
  compliance   : SSdfControlMap, PhaseGContract, TelemetryInitializer T0-T7
  runtime      : AD2026Runtime bootstrap, execute_sps full pipeline
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from udgs_core.ad2026.identity import (
    AAID, ACRootKey, APBChain, EvidenceKind, EvidenceRef,
    JWS_ALG, ENV_CLASS_NO_TEE,
    _canonical_json, _sha256hex,
    jws_sign, jws_verify, zto_verify,
)
from udgs_core.ad2026.typed_plan import (
    TypedAction, ActionType, SPS, Invariant,
    InvariantSet, SMTGate, SPSValidator,
    build_ac_baseline_invariants, GateResult,
)
from udgs_core.ad2026.gates import (
    G6Auth, G7Formal, G8Sandbox, G9MCP, G10Sync, G11InvariantFixation,
    GateStatus, GateRunResult, GateRunnerResult,
    EnvironmentProfile, MCPPolicy, MCPCallRecord, RCToken,
    CIL9Snapshot, CIL10Snapshot,
)
from udgs_core.ad2026.cognitive import (
    CIL9Metrics, BSSPlanner, CRSMBoundary, CRSMEpoch,
    PeripheralMutation, UDSInput,
)
from udgs_core.ad2026.compliance import (
    SSdfControlMap, SSdfPhase, PhaseGContract,
    TelemetryInitializer, build_default_phase_g_contract,
)
from udgs_core.ad2026.runtime import (
    AD2026Runtime, ArchitectureConstitution, build_default_ac,
)


# ═══════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════

@pytest.fixture
def aaid():
    return AAID.generate("test-agent")

@pytest.fixture
def ac_root_key():
    return ACRootKey.generate()

@pytest.fixture
def ac():
    return build_default_ac()

@pytest.fixture
def ac_signed(ac, ac_root_key):
    return ac_root_key.sign_ac(ac.canonical_bytes())

@pytest.fixture
def runtime(tmp_path):
    return AD2026Runtime.bootstrap(root=str(tmp_path), agent_id="TEST-AGENT")

@pytest.fixture
def sample_sps():
    from datetime import datetime, timezone
    sps = SPS(
        sps_id="TEST-SPS-001",
        agent_id="test-agent",
        utc=datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    sps.add(TypedAction(
        action_id="ACT-001",
        action_type=ActionType.CHECKPOINT,
        preconditions=["system_ready"],
        postconditions=["checkpoint_written"],
        invariants_touched=["DETERMINISM-01"],
        rollback_action_id="NOOP",
        evidence_refs=["§REF:LOG#test#" + "0"*64],
    ))
    sps.add(TypedAction(
        action_id="ACT-002",
        action_type=ActionType.EMIT_PB,
        preconditions=["checkpoint_written"],
        postconditions=["pb_emitted"],
        invariants_touched=[],
        rollback_action_id="NOOP",
    ))
    return sps

@pytest.fixture
def mcp_policy():
    token = RCToken(
        token_id="TOK-001",
        agent_id="test-agent",
        capabilities=["READ", "WRITE", "CHECKPOINT"],
        expires_utc="2026-12-31T23:59:59Z",
    )
    return MCPPolicy({"TOK-001": token})


# ═══════════════════════════════════════════════════════
# L0 IDENTITY
# ═══════════════════════════════════════════════════════

class TestAAID:
    def test_generate_creates_keypair(self):
        a = AAID.generate("agent-x")
        assert a.agent_id == "agent-x"
        assert a.env_class == ENV_CLASS_NO_TEE
        assert len(a.public_id) == 32

    def test_sign_verify_roundtrip(self, aaid):
        payload = b"test payload"
        mac = aaid.sign(payload)
        assert aaid.verify(payload, mac)

    def test_verify_wrong_payload_fails(self, aaid):
        mac = aaid.sign(b"correct")
        assert not aaid.verify(b"tampered", mac)

    def test_different_agents_different_keys(self):
        a1 = AAID.generate("a1")
        a2 = AAID.generate("a2")
        payload = b"same payload"
        assert a1.sign(payload) != a2.sign(payload)

    def test_public_id_deterministic(self):
        a = AAID.generate("x")
        assert a.public_id == a.public_id

    def test_as_public_dict_no_secret(self, aaid):
        d = aaid.as_public_dict()
        assert "agent_id" in d
        assert "_secret" not in str(d)


class TestACRootKey:
    def test_sign_verify_ac(self, ac_root_key, ac):
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        assert ac_root_key.verify_ac(ac.canonical_bytes(), sig)

    def test_wrong_ac_fails_verify(self, ac_root_key, ac):
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        tampered = ac.canonical_bytes() + b"x"
        assert not ac_root_key.verify_ac(tampered, sig)

    def test_save_load_roundtrip(self, tmp_path, ac_root_key, ac):
        path = str(tmp_path / "key.json")
        ac_root_key.save(path)
        loaded = ACRootKey.load(path)
        sig = loaded.sign_ac(ac.canonical_bytes())
        assert ac_root_key.verify_ac(ac.canonical_bytes(), sig)


class TestJWS:
    def test_sign_verify_roundtrip(self, aaid):
        payload = {"action": "test", "value": 42}
        token = jws_sign(payload, aaid)
        valid, decoded = jws_verify(token, aaid)
        assert valid
        assert decoded["action"] == "test"

    def test_tampered_payload_fails(self, aaid):
        token = jws_sign({"x": 1}, aaid)
        parts = token.split(".")
        # Tamper middle part
        import base64
        bad = base64.urlsafe_b64encode(b'{"x":99}').rstrip(b"=").decode()
        tampered = f"{parts[0]}.{bad}.{parts[2]}"
        valid, _ = jws_verify(tampered, aaid)
        assert not valid

    def test_wrong_agent_fails(self, aaid):
        token = jws_sign({"x": 1}, aaid)
        other = AAID.generate("other")
        valid, _ = jws_verify(token, other)
        assert not valid

    def test_three_part_structure(self, aaid):
        token = jws_sign({}, aaid)
        assert len(token.split(".")) == 3


class TestAPBChain:
    def _make_chain(self, aaid, ac):
        return APBChain(
            aaid=aaid,
            ac_version_sha256=ac.sha256(),
            toolchain_pins_hash="a"*64,
            env_fingerprint_hash="b"*64,
        )

    def test_append_increments_counter(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        b1 = chain.append({"in":1}, {"out":1}, {"G6":"PASS"})
        b2 = chain.append({"in":2}, {"out":2}, {"G6":"PASS"})
        assert b1.monotonic_counter == 1
        assert b2.monotonic_counter == 2

    def test_chain_continuity(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        chain.append({"in":1}, {"out":1}, {"G6":"PASS"})
        chain.append({"in":2}, {"out":2}, {"G6":"PASS"})
        valid, errors = chain.verify_chain()
        assert valid, errors

    def test_genesis_prev_hash_empty(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        b = chain.append({"in":1}, {"out":1}, {})
        assert b.prev_bundle_hash == ""

    def test_chain_break_detected(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        chain.append({"in":1}, {"out":1}, {})
        chain._chain[-1].prev_bundle_hash = "tampered"*8  # break chain
        _, errors = chain.verify_chain()
        assert len(errors) > 0

    def test_jws_in_every_bundle(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        for i in range(5):
            b = chain.append({"i":i}, {"o":i}, {})
            assert len(b.jws_token.split(".")) == 3

    def test_evidence_refs_attached(self, aaid, ac):
        chain = self._make_chain(aaid, ac)
        refs = [EvidenceRef(kind=EvidenceKind.LOG, id="test-001", sha256="a"*64)]
        b = chain.append({"in":1}, {"out":1}, {}, evidence_refs=refs)
        assert "§REF:LOG#test-001" in b.evidence_refs[0]


class TestZTOVerify:
    def test_valid_zto_passes(self, aaid, ac_root_key, ac):
        chain = APBChain(aaid=aaid, ac_version_sha256=ac.sha256(),
                         toolchain_pins_hash="a"*64, env_fingerprint_hash="b"*64)
        bundle = chain.append({"in":1}, {"out":1}, {})
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        ok, errors = zto_verify(bundle, aaid, ac_root_key, ac.canonical_bytes(), sig, "")
        assert ok, errors

    def test_wrong_aaid_fails(self, aaid, ac_root_key, ac):
        chain = APBChain(aaid=aaid, ac_version_sha256=ac.sha256(),
                         toolchain_pins_hash="a"*64, env_fingerprint_hash="b"*64)
        bundle = chain.append({}, {}, {})
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        other_aaid = AAID.generate("other")
        ok, errors = zto_verify(bundle, other_aaid, ac_root_key, ac.canonical_bytes(), sig, "")
        assert not ok

    def test_chain_break_detected(self, aaid, ac_root_key, ac):
        chain = APBChain(aaid=aaid, ac_version_sha256=ac.sha256(),
                         toolchain_pins_hash="a"*64, env_fingerprint_hash="b"*64)
        bundle = chain.append({}, {}, {})
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        ok, errors = zto_verify(bundle, aaid, ac_root_key, ac.canonical_bytes(), sig,
                                expected_prev_hash="wrong_hash")
        assert not ok
        assert any("chain break" in e for e in errors)


class TestEvidenceRef:
    def test_str_format(self):
        ref = EvidenceRef(kind=EvidenceKind.LOG, id="test-001", sha256="a"*64)
        assert str(ref) == "§REF:LOG#test-001#" + "a"*64

    def test_roundtrip(self):
        ref = EvidenceRef(kind=EvidenceKind.ATTEST, id="attest-xyz", sha256="f"*64)
        assert EvidenceRef.from_str(str(ref)) == ref

    def test_from_bytes(self):
        ref = EvidenceRef.from_bytes(EvidenceKind.TEST, "test-001", b"content")
        assert len(ref.sha256) == 64

    def test_invalid_ref_raises(self):
        with pytest.raises(ValueError):
            EvidenceRef.from_str("INVALID")


# ═══════════════════════════════════════════════════════
# L1 TYPED PLAN
# ═══════════════════════════════════════════════════════

class TestTypedAction:
    def test_serialization(self):
        a = TypedAction(
            action_id="A1",
            action_type=ActionType.DEPLOY,
            preconditions=["pre1"],
            postconditions=["post1"],
            invariants_touched=["SAFETY-01"],
            rollback_action_id="RB-1",
            evidence_refs=["§REF:LOG#x#" + "0"*64],
        )
        d = a.as_dict()
        assert d["action_type"] == "DEPLOY"
        assert d["rollback_action_id"] == "RB-1"


class TestSPS:
    def test_sha256_deterministic(self, sample_sps):
        assert sample_sps.sha256() == sample_sps.sha256()

    def test_sha256_changes_on_mutation(self, sample_sps):
        h1 = sample_sps.sha256()
        sample_sps.add(TypedAction(
            action_id="NEW", action_type=ActionType.READ,
            preconditions=[], postconditions=[],
            invariants_touched=[], rollback_action_id="NOOP",
        ))
        assert sample_sps.sha256() != h1

    def test_canonical_bytes_stable(self, sample_sps):
        assert sample_sps.canonical_bytes() == sample_sps.canonical_bytes()


class TestInvariantSet:
    def test_empty_set_pass(self, sample_sps):
        inv_set = InvariantSet()
        ok, v = inv_set.evaluate(sample_sps)
        assert ok and not v

    def test_violated_invariant_detected(self, sample_sps):
        inv_set = InvariantSet()
        inv_set.register(Invariant(
            invariant_id="TEST-01", kind="SAFETY",
            description="Always fail",
            predicate=lambda sps: False,
        ))
        ok, v = inv_set.evaluate(sample_sps)
        assert not ok
        assert "TEST-01" in v[0]

    def test_all_baseline_invariants_pass_valid_sps(self, sample_sps):
        inv_set = build_ac_baseline_invariants()
        ok, v = inv_set.evaluate(sample_sps)
        assert ok, v


class TestSMTGate:
    def test_valid_sps_proves(self, sample_sps):
        gate = SMTGate(build_ac_baseline_invariants())
        result = gate.prove(sample_sps)
        assert result.passed

    def test_empty_sps_fails_safety02(self):
        from datetime import datetime, timezone
        gate = SMTGate(build_ac_baseline_invariants())
        empty_sps = SPS("EMPTY", "agent", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        result = gate.prove(empty_sps)
        assert not result.passed
        assert any("SAFETY-02" in v for v in result.violations)

    def test_deploy_without_rollback_fails_safety01(self):
        from datetime import datetime, timezone
        gate = SMTGate(build_ac_baseline_invariants())
        sps = SPS("BAD", "agent", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        sps.add(TypedAction(
            action_id="D1", action_type=ActionType.DEPLOY,
            preconditions=["pre"], postconditions=["post"],
            invariants_touched=[], rollback_action_id="",  # missing rollback
            evidence_refs=["§REF:LOG#x#"+"0"*64],
        ))
        result = gate.prove(sps)
        assert not result.passed
        assert any("SAFETY-01" in v for v in result.violations)

    def test_kernel_mutation_fails_forbidden01(self):
        from datetime import datetime, timezone
        gate = SMTGate(build_ac_baseline_invariants())
        sps = SPS("KERN", "agent", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        sps.add(TypedAction(
            action_id="M1", action_type=ActionType.MUTATE_PERIPHERAL,
            preconditions=[], postconditions=[],
            invariants_touched=["AC_KERNEL_integrity"],
            rollback_action_id="NOOP",
        ))
        sps.add(TypedAction(
            action_id="PB1", action_type=ActionType.EMIT_PB,
            preconditions=[], postconditions=[],
            invariants_touched=[], rollback_action_id="NOOP",
        ))
        result = gate.prove(sps)
        assert not result.passed

    def test_no_invariants_returns_error(self, sample_sps):
        gate = SMTGate(InvariantSet())
        result = gate.prove(sample_sps)
        assert result.status == "ERROR"


class TestSPSValidator:
    def test_valid_sps_passes(self, sample_sps):
        ok, errors = SPSValidator.validate(sample_sps)
        assert ok, errors

    def test_missing_rollback_reference_detected(self):
        from datetime import datetime, timezone
        sps = SPS("T", "a", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        sps.add(TypedAction(
            action_id="A1", action_type=ActionType.DEPLOY,
            preconditions=["p"], postconditions=["q"],
            invariants_touched=[], rollback_action_id="NONEXISTENT",
            evidence_refs=["§REF:LOG#x#"+"0"*64],
        ))
        ok, errors = SPSValidator.validate(sps)
        assert not ok
        assert any("NONEXISTENT" in e for e in errors)

    def test_deploy_without_evidence_detected(self):
        from datetime import datetime, timezone
        sps = SPS("T", "a", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        sps.add(TypedAction(
            action_id="A1", action_type=ActionType.DEPLOY,
            preconditions=["p"], postconditions=["q"],
            invariants_touched=[], rollback_action_id="NOOP",
            evidence_refs=[],  # missing
        ))
        ok, errors = SPSValidator.validate(sps)
        assert not ok
        assert any("evidence_refs" in e for e in errors)


# ═══════════════════════════════════════════════════════
# GATES G6–G11
# ═══════════════════════════════════════════════════════

class TestG6Auth:
    def _make_bundle(self, aaid, ac):
        chain = APBChain(aaid=aaid, ac_version_sha256=ac.sha256(),
                         toolchain_pins_hash="a"*64, env_fingerprint_hash="b"*64)
        return chain.append({}, {}, {}), chain

    def test_valid_passes(self, aaid, ac_root_key, ac):
        bundle, _ = self._make_bundle(aaid, ac)
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        g6 = G6Auth()
        r = g6.run(bundle, aaid, ac_root_key, ac.canonical_bytes(), sig, "")
        assert r.passed

    def test_wrong_aaid_fails(self, aaid, ac_root_key, ac):
        bundle, _ = self._make_bundle(aaid, ac)
        sig = ac_root_key.sign_ac(ac.canonical_bytes())
        g6 = G6Auth()
        other = AAID.generate("other")
        r = g6.run(bundle, other, ac_root_key, ac.canonical_bytes(), sig, "")
        assert not r.passed


class TestG7Formal:
    def test_valid_sps_passes(self, sample_sps):
        g7 = G7Formal(SMTGate(build_ac_baseline_invariants()))
        r = g7.run(sample_sps)
        assert r.passed

    def test_invariant_violation_fails(self):
        from datetime import datetime, timezone
        g7 = G7Formal(SMTGate(build_ac_baseline_invariants()))
        sps = SPS("BAD", "a", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        r = g7.run(sps)
        assert not r.passed


class TestG8Sandbox:
    def test_matching_env_passes(self):
        profile = EnvironmentProfile(
            profile_id="P1", python_version="3.12", platform="linux",
            toolchain_pins={"pytest": "9.0"},
        )
        fp = profile.compute_fingerprint()
        tc = hashlib.sha256(b"toolchain").hexdigest()
        g8 = G8Sandbox()
        r = g8.run(profile, fp, tc, tc)
        assert r.passed

    def test_env_mismatch_fails(self):
        profile = EnvironmentProfile(
            profile_id="P1", python_version="3.12", platform="linux",
            toolchain_pins={"pytest": "9.0"},
        )
        profile.compute_fingerprint()
        g8 = G8Sandbox()
        r = g8.run(profile, "wrong_fp"*4, "tc_hash"*8, "tc_hash"*8)
        assert not r.passed

    def test_toolchain_mismatch_fails(self):
        profile = EnvironmentProfile(
            profile_id="P1", python_version="3.12", platform="linux",
            toolchain_pins={},
        )
        fp = profile.compute_fingerprint()
        g8 = G8Sandbox()
        r = g8.run(profile, fp, "expected"*8, "different"*8)
        assert not r.passed


class TestG9MCP:
    def test_valid_hermetic_call_passes(self, mcp_policy):
        call = MCPCallRecord(
            call_id="C1", tool_name="read_file", token_id="TOK-001",
            input_hash="a"*64, output_hash="b"*64,
            timestamp_utc="2026-01-01T00:00:00Z", hermetic=True,
        )
        g9 = G9MCP(mcp_policy)
        r = g9.run([(call, "READ")])
        assert r.passed

    def test_non_hermetic_fails(self, mcp_policy):
        call = MCPCallRecord(
            call_id="C2", tool_name="tool", token_id="TOK-001",
            input_hash="a"*64, output_hash="b"*64,
            timestamp_utc="2026-01-01T00:00:00Z", hermetic=False,
        )
        g9 = G9MCP(mcp_policy)
        r = g9.run([(call, "READ")])
        assert not r.passed

    def test_missing_capability_fails(self, mcp_policy):
        call = MCPCallRecord(
            call_id="C3", tool_name="tool", token_id="TOK-001",
            input_hash="a"*64, output_hash="b"*64,
            timestamp_utc="2026-01-01T00:00:00Z", hermetic=True,
        )
        g9 = G9MCP(mcp_policy)
        r = g9.run([(call, "EXECUTE")])  # EXECUTE not in token
        assert not r.passed

    def test_revoked_token_fails(self, mcp_policy):
        mcp_policy._tokens["TOK-001"].revoked = True
        call = MCPCallRecord(
            call_id="C4", tool_name="tool", token_id="TOK-001",
            input_hash="a"*64, output_hash="b"*64,
            timestamp_utc="2026-01-01T00:00:00Z", hermetic=True,
        )
        g9 = G9MCP(mcp_policy)
        r = g9.run([(call, "READ")])
        assert not r.passed
        mcp_policy._tokens["TOK-001"].revoked = False  # restore


class TestG10Sync:
    def test_all_thresholds_met_passes(self):
        snap = CIL9Snapshot(
            predictive_precision=0.95,
            alignment_score=0.99,
            latency_ms=300.0,
            drift_correction_success=0.995,
            planner_mismatch_count=0,
        )
        g10 = G10Sync()
        r = g10.run(snap)
        assert r.passed

    def test_low_precision_fails(self):
        snap = CIL9Snapshot(
            predictive_precision=0.90,  # below 0.94
            alignment_score=0.99,
            latency_ms=300.0,
            drift_correction_success=0.995,
            planner_mismatch_count=0,
        )
        r = G10Sync().run(snap)
        assert not r.passed

    def test_high_latency_fails(self):
        snap = CIL9Snapshot(
            predictive_precision=0.95,
            alignment_score=0.99,
            latency_ms=600.0,  # above 500ms
            drift_correction_success=0.995,
            planner_mismatch_count=0,
        )
        r = G10Sync().run(snap)
        assert not r.passed

    def test_mismatch_nonzero_fails(self):
        snap = CIL9Snapshot(
            predictive_precision=0.95,
            alignment_score=0.99,
            latency_ms=300.0,
            drift_correction_success=0.995,
            planner_mismatch_count=1,
        )
        r = G10Sync().run(snap)
        assert not r.passed

    def test_ac_violations_in_window_fails(self):
        snap = CIL9Snapshot(0.95, 0.99, 300.0, 0.995, 0)
        r = G10Sync().run(snap, ac_violations_in_window=1)
        assert not r.passed


class TestG11InvariantFixation:
    def _good_snap(self, sha="abc"):
        return CIL10Snapshot(
            invariant_integrity=1.0,
            ac_sha256_before=sha, ac_sha256_after=sha,
            optimization_delta=0.20,
            safety_entropy=0.0,
            replay_mismatch_m=0, replay_n=100, min_replay_n=100,
            ssdf_regression=False, phase_g_pass=True, change_failure_rate=0.0,
        )

    def test_perfect_snapshot_passes(self):
        snap = self._good_snap("a"*64)
        r = G11InvariantFixation().run(snap)
        assert r.passed

    def test_integrity_not_1_fails(self):
        snap = self._good_snap("a"*64)
        snap.invariant_integrity = 0.9
        r = G11InvariantFixation().run(snap)
        assert not r.passed

    def test_ac_hash_changed_fails(self):
        snap = self._good_snap("a"*64)
        snap.ac_sha256_after = "b"*64
        r = G11InvariantFixation().run(snap)
        assert not r.passed

    def test_replay_mismatch_fails(self):
        snap = self._good_snap("a"*64)
        snap.replay_mismatch_m = 1
        r = G11InvariantFixation().run(snap)
        assert not r.passed

    def test_insufficient_n_returns_not_ready(self):
        snap = self._good_snap("a"*64)
        snap.replay_n = 50
        snap.min_replay_n = 100
        r = G11InvariantFixation().run(snap)
        assert r.status == GateStatus.NOT_READY

    def test_ssdf_regression_fails(self):
        snap = self._good_snap("a"*64)
        snap.ssdf_regression = True
        r = G11InvariantFixation().run(snap)
        assert not r.passed

    def test_nonzero_cfr_fails(self):
        snap = self._good_snap("a"*64)
        snap.change_failure_rate = 0.01
        r = G11InvariantFixation().run(snap)
        assert not r.passed


# ═══════════════════════════════════════════════════════
# L4 COGNITIVE
# ═══════════════════════════════════════════════════════

class TestCIL9Metrics:
    def test_perfect_metrics_snapshot(self):
        m = CIL9Metrics()
        for _ in range(20):
            m.record_attempt(correct=True, latency_ms=100.0)
            m.record_alignment(score=1.0)
            m.record_drift_correction(success=True)
            m.record_planner_replay(mismatch=False)
        snap = m.snapshot()
        assert snap.predictive_precision == 1.0
        assert snap.alignment_score == 1.0
        assert snap.planner_mismatch_count == 0
        assert not snap.violations()

    def test_degraded_metrics_detected(self):
        m = CIL9Metrics()
        for _ in range(100):
            m.record_attempt(correct=False, latency_ms=600.0)
            m.record_alignment(score=0.5)
        snap = m.snapshot()
        v = snap.violations()
        assert len(v) > 0

    def test_empty_metrics_defaults_to_thresholds(self):
        snap = CIL9Metrics().snapshot()
        assert snap.predictive_precision == 1.0
        assert snap.alignment_score == 1.0


class TestBSSPlanner:
    def _uds(self, intent="verify"):
        return UDSInput(
            intent=intent,
            constraints=["fail-closed"],
            objective="stable",
            ac_sha256="a"*64,
            policy_pack_sha256="b"*64,
            telemetry_hash="c"*64,
        )

    def test_plan_returns_sps(self):
        planner = BSSPlanner("agent", "a"*64, {})
        sps, score = planner.plan(self._uds())
        assert len(sps.actions) > 0
        assert 0.0 <= score <= 1.0

    def test_deterministic_same_input(self):
        planner = BSSPlanner("agent", "a"*64, {})
        uds = self._uds("same intent")
        sps1, _ = planner.plan(uds)
        sps2, _ = planner.plan(uds)
        assert sps1.sha256() == sps2.sha256()

    def test_different_intent_different_sps(self):
        planner = BSSPlanner("agent", "a"*64, {})
        sps1, _ = planner.plan(self._uds("intent-A"))
        sps2, _ = planner.plan(self._uds("intent-B"))
        assert sps1.sha256() != sps2.sha256()

    def test_replay_n100_zero_mismatches(self):
        planner = BSSPlanner("agent", "a"*64, {})
        m, n = planner.replay_n(self._uds(), n=100)
        assert m == 0
        assert n == 100

    def test_metrics_accumulate(self):
        m = CIL9Metrics()
        planner = BSSPlanner("agent", "a"*64, {}, metrics=m)
        for _ in range(10):
            planner.plan(self._uds())
        snap = m.snapshot()
        assert snap.predictive_precision >= 0.94


class TestCRSMBoundary:
    def _epoch(self, ac_sha):
        return CRSMEpoch(
            epoch_id="E1",
            ac_sha256=ac_sha,
            mutations=[
                PeripheralMutation(
                    epoch_id="E1-M1",
                    component="routing_policy",
                    before_sha256="a"*64,
                    after_sha256="b"*64,
                    rationale="Improve routing",
                    rollback_sha256="a"*64,
                    reversible=True,
                    attested=True,
                )
            ],
            optimization_before=0.70,
            optimization_after=0.90,
            replay_m=0, replay_n=100,
            ssdf_regression=False, phase_g_pass=True, cfr=0.0, safety_entropy=0.0,
        )

    def test_kernel_integrity_preserved(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        ok, msg = crsm.check_kernel_integrity(sha)
        assert ok

    def test_kernel_modification_halts(self):
        crsm = CRSMBoundary("a"*64, min_replay_n=100)
        ok, msg = crsm.check_kernel_integrity("b"*64)
        assert not ok
        assert crsm.halted
        assert "HARD-KILL" in msg

    def test_valid_peripheral_mutation_approved(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        ok, errors = crsm.propose_mutation(self._epoch(sha), sha)
        assert ok, errors

    def test_non_reversible_mutation_rejected(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        epoch = self._epoch(sha)
        epoch.mutations[0].reversible = False
        ok, errors = crsm.propose_mutation(epoch, sha)
        assert not ok

    def test_unattest_mutation_rejected(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        epoch = self._epoch(sha)
        epoch.mutations[0].attested = False
        ok, errors = crsm.propose_mutation(epoch, sha)
        assert not ok

    def test_hard_kill_stops_further_mutations(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        crsm.hard_kill(sha)
        ok, errors = crsm.propose_mutation(self._epoch(sha), sha)
        assert not ok
        assert any("halted" in e for e in errors)

    def test_commit_produces_ci_l10_snapshot(self):
        sha = "a"*64
        crsm = CRSMBoundary(sha, min_replay_n=100)
        snap = crsm.commit_epoch(self._epoch(sha), sha)
        assert snap.invariant_integrity == 1.0
        assert snap.optimization_delta == pytest.approx(0.20)


# ═══════════════════════════════════════════════════════
# COMPLIANCE
# ═══════════════════════════════════════════════════════

class TestSSdfControlMap:
    def test_baseline_has_controls(self):
        m = SSdfControlMap()
        assert len(m._controls) > 0

    def test_satisfy_marks_control(self):
        m = SSdfControlMap()
        ok = m.satisfy("SSDF-P.1.1", evidence_ref="§REF:DOC#policy#"+"0"*64)
        assert ok
        c = next(x for x in m._controls if x.control_id == "SSDF-P.1.1")
        assert c.satisfied

    def test_coverage_increases_on_satisfy(self):
        m = SSdfControlMap()
        cov0 = m.coverage()
        m.satisfy("SSDF-P.1.1")
        assert m.coverage() > cov0

    def test_regression_guard_detects_regression(self):
        m = SSdfControlMap()
        m.satisfy("SSDF-P.1.1")
        m.enable_regression_guard()
        # Manually mark a satisfied control as unsatisfied
        for c in m._controls:
            if c.satisfied:
                c.satisfied = False
                break
        assert m.has_regression()

    def test_no_regression_when_guard_disabled(self):
        m = SSdfControlMap()
        assert not m.has_regression()


class TestPhaseGContract:
    def test_default_contract_populated(self):
        c = build_default_phase_g_contract()
        assert c.is_populated()

    def test_empty_contract_not_populated(self):
        c = PhaseGContract(
            contract_id="X",
            deliverables=[],
            compliance_checkpoints=[],
            gate_criteria={},
            verification_obligations=[],
            deployment_conditions=[],
            rollback_conditions=[],
        )
        assert not c.is_populated()


class TestTelemetryInitializer:
    def test_all_pending_initially(self):
        t = TelemetryInitializer()
        assert not t.execution_ready
        assert t.autonomy_status == "AUTONOMY_OFF"

    def test_run_check_marks_status(self):
        t = TelemetryInitializer()
        t.run_check("T0", lambda: (True, "test evidence"))
        assert t._checks["T0"].status == "PASS"

    def test_failing_check_blocks_execution(self):
        t = TelemetryInitializer()
        for cid in ["T0","T1","T2","T3","T4","T5","T6"]:
            t.mark(cid, status="PASS")
        t.mark("T7", status="FAIL")
        assert not t.execution_ready

    def test_all_pass_gives_hardened_determinism(self):
        t = TelemetryInitializer()
        for cid in ["T0","T1","T2","T3","T4","T5","T6","T7"]:
            t.mark(cid, status="PASS")
        assert t.execution_ready
        assert t.autonomy_status == "HARDENED_DETERMINISM"


# ═══════════════════════════════════════════════════════
# AD2026 RUNTIME — Integration
# ═══════════════════════════════════════════════════════

class TestAD2026Runtime:
    def test_bootstrap_creates_state_dir(self, tmp_path):
        rt = AD2026Runtime.bootstrap(root=str(tmp_path))
        assert os.path.isdir(str(tmp_path / "ad2026_state"))

    def test_bootstrap_generates_ac_root_key(self, tmp_path):
        AD2026Runtime.bootstrap(root=str(tmp_path))
        assert os.path.exists(str(tmp_path / "ad2026_state" / "AC_ROOT_KEY.json"))

    def test_bootstrap_key_reused_on_second_call(self, tmp_path):
        rt1 = AD2026Runtime.bootstrap(root=str(tmp_path))
        rt2 = AD2026Runtime.bootstrap(root=str(tmp_path))
        assert rt1.ac.sha256() == rt2.ac.sha256()

    def test_telemetry_checklist_all_pass(self, runtime):
        result = runtime.run_telemetry_checklist()
        assert result["execution_ready"], result["checks"]
        for cid, check in result["checks"].items():
            assert check["status"] == "PASS", f"{cid} FAILED: {check['evidence']}"

    def test_execute_sps_nominal_all_gates_pass(self, runtime, sample_sps):
        telemetry_ready = {"execution_ready": True, "checks": {}}
        ideal_snapshot = CIL9Snapshot(
            predictive_precision=1.0,
            alignment_score=1.0,
            latency_ms=0.0,
            drift_correction_success=1.0,
            planner_mismatch_count=0,
        )
        with patch.object(runtime, "run_telemetry_checklist", return_value=telemetry_ready), \
             patch.object(runtime.metrics, "snapshot", return_value=ideal_snapshot):
            runtime.run_telemetry_checklist()
            result = runtime.execute_sps(sample_sps)
        assert result["execution_allowed"] is True, f"Gates failed: {result.get('gate_reports')}"
        for gate in result["gates"]["gates"]:
            assert gate["status"] == "PASS", gate

    def test_execute_sps_writes_log(self, runtime, sample_sps):
        runtime.run_telemetry_checklist()
        runtime.execute_sps(sample_sps)
        log_path = os.path.join(runtime.state_dir, "AD2026_EXECUTION_LOG.jsonl")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            entry = json.loads(f.readlines()[-1])
        assert entry["sps_id"] == sample_sps.sps_id
        assert entry["execution_allowed"] is True

    def test_execute_invalid_sps_blocked(self, runtime):
        from datetime import datetime, timezone
        runtime.run_telemetry_checklist()
        bad_sps = SPS("BAD", "agent", datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        result = runtime.execute_sps(bad_sps)
        assert not result["execution_allowed"]
        assert any(g["status"] == "FAIL" for g in result["gates"]["gates"])

    def test_apb_chain_grows_on_each_execute(self, runtime, sample_sps):
        runtime.run_telemetry_checklist()
        n0 = len(runtime.apb_chain)
        runtime.execute_sps(sample_sps)
        runtime.execute_sps(sample_sps)
        assert len(runtime.apb_chain) == n0 + 4  # 2 pre + 2 final

    def test_status_written_to_file(self, runtime):
        runtime.run_telemetry_checklist()
        s = runtime.status()
        assert os.path.exists(os.path.join(runtime.state_dir, "AD2026_STATUS.json"))
        assert s["grade"] == "AD-2026-INTEGRATED"
        assert s["ac_version"] == "AD-2026-v2.2"

    def test_crsm_kernel_integrity_preserved(self, runtime):
        assert not runtime.crsm.halted
        ok, _ = runtime.crsm.check_kernel_integrity(runtime.ac.sha256())
        assert ok

    def test_apb_chain_verifies(self, runtime, sample_sps):
        runtime.run_telemetry_checklist()
        runtime.execute_sps(sample_sps)
        ok, errors = runtime.apb_chain.verify_chain()
        assert ok, errors

    def test_ssdf_coverage_after_init(self, runtime):
        runtime.run_telemetry_checklist()
        assert runtime.ssdf_map.coverage() > 0.0

    def test_phase_g_populated(self, runtime):
        assert runtime.phase_g.is_populated()
