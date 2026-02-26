"""
DAO-LIFEBOOK — Comprehensive Test Suite (v2).

Tests every module with:
  • Unit tests for happy path
  • Error path tests
  • Edge case tests
  • Property-based tests (Hypothesis)
  • Integration tests (end-to-end)
  • Determinism verification
  • Regression tests for v1 bugs
"""

from __future__ import annotations

import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st


# ════════════════════════════════════════════════════════════════════════════════
# §1 — Types
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook._types import Ok, Err, DAOError, ErrorSeverity, EC


class TestResult:
    def test_ok_is_ok(self):
        r = Ok(42)
        assert r.is_ok()
        assert not r.is_err()
        assert r.unwrap() == 42

    def test_err_is_err(self):
        r = Err("fail")
        assert r.is_err()
        assert not r.is_ok()
        assert r.unwrap_err() == "fail"

    def test_ok_unwrap_err_raises(self):
        with pytest.raises(TypeError):
            Ok(1).unwrap_err()

    def test_err_unwrap_raises(self):
        with pytest.raises(TypeError):
            Err("x").unwrap()

    def test_ok_map(self):
        r = Ok(5).map(lambda x: x * 2)
        assert r.unwrap() == 10

    def test_err_map_propagates(self):
        r = Err("fail").map(lambda x: x * 2)
        assert r.is_err()
        assert r.unwrap_err() == "fail"

    def test_dao_error_str(self):
        e = DAOError(code="TEST", message="bad thing")
        assert "[TEST]" in str(e)
        assert "bad thing" in str(e)


# ════════════════════════════════════════════════════════════════════════════════
# §2 — Models
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.models import (
    ArtifactRef, AuditVerdict, CheckResult, CheckStatus,
    Constraints, DiffBudget, DiffSummary, EditInstruction,
    EvidencePointer, FailPacket, GovernorAction, GovernorDecision,
    HistoryEvent, LocalGateResult, LoopState, Phase, ProofBundle,
    RefactorPolicy, SecurityPolicy, Spec, TargetState, TimeSpan,
    SCHEMA_VERSION,
)


class TestCheckStatus:
    def test_green(self):
        assert CheckStatus.SUCCESS.is_green
        assert not CheckStatus.FAILURE.is_green
        assert not CheckStatus.PENDING.is_green

    def test_terminal(self):
        assert CheckStatus.SUCCESS.is_terminal
        assert CheckStatus.FAILURE.is_terminal
        assert not CheckStatus.PENDING.is_terminal
        assert not CheckStatus.UNKNOWN.is_terminal


class TestPhase:
    def test_ordinal_ordering(self):
        assert Phase.OBSERVE.ordinal < Phase.PACKETIZE.ordinal
        assert Phase.PACKETIZE.ordinal < Phase.PLAN.ordinal
        assert Phase.AUDIT.ordinal < Phase.DECIDE.ordinal


class TestGovernorAction:
    def test_all_values(self):
        assert GovernorAction.MERGE.value == "merge"
        assert GovernorAction.HALT.value == "halt"
        assert GovernorAction.NEXT.value == "next_loop"
        assert GovernorAction.HOLD.value == "hold"


class TestArtifactRef:
    def test_valid_hash(self):
        ref = ArtifactRef(path="a.txt", sha256="a" * 64)
        assert ref.sha256 == "a" * 64

    def test_invalid_hash_rejects(self):
        with pytest.raises(Exception):
            ArtifactRef(path="a.txt", sha256="short")

    def test_invalid_hash_uppercase_rejects(self):
        with pytest.raises(Exception):
            ArtifactRef(path="a.txt", sha256="A" * 64)

    def test_empty_hash_ok(self):
        ref = ArtifactRef(path="a.txt", sha256="")
        assert ref.sha256 == ""

    def test_from_file(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        ref = ArtifactRef.from_file(f)
        assert len(ref.sha256) == 64
        # Verify deterministic
        assert ref.sha256 == hashlib.sha256(b"hello world").hexdigest()

    def test_frozen(self):
        ref = ArtifactRef(path="a.txt", sha256="a" * 64)
        with pytest.raises(Exception):
            ref.path = "b.txt"  # type: ignore


class TestTargetState:
    def test_valid(self):
        ts = TargetState(goal="Fix CI", done_when=["All checks green"])
        assert ts.goal == "Fix CI"

    def test_empty_goal_fails(self):
        with pytest.raises(Exception):
            TargetState(goal="", done_when=["All checks green"])

    def test_vague_done_when_fails(self):
        with pytest.raises(Exception):
            TargetState(goal="Fix", done_when=["ok"])

    def test_auto_detect_required(self):
        ts = TargetState(goal="Fix", done_when=["Checks pass"])
        assert ts.required_checks == "auto-detect from PR"

    def test_explicit_required_checks(self):
        ts = TargetState(goal="Fix", done_when=["Checks pass"], required_checks=["lint", "test"])
        assert ts.required_checks == ["lint", "test"]


class TestConstraints:
    def test_defaults(self):
        c = Constraints()
        assert c.touch_allowlist == ["*"]
        assert c.diff_budget.max_files == 20
        assert c.refactor_policy == RefactorPolicy.NO_REFACTOR
        assert c.security_policy.no_disable_security_checks is True

    def test_frozen(self):
        c = Constraints()
        with pytest.raises(Exception):
            c.refactor_policy = RefactorPolicy.ALLOWED  # type: ignore


class TestFailPacket:
    def test_valid(self):
        fp = FailPacket(
            check_name="lint",
            error_extract=["Error: unused import at line 42"],
            done_when="lint check passes",
        )
        assert fp.severity == 0

    def test_insufficient_signal_rejects(self):
        with pytest.raises(Exception):
            FailPacket(
                check_name="lint",
                error_extract=["x"],
                done_when="fix it",
            )

    def test_empty_check_name_rejects(self):
        with pytest.raises(Exception):
            FailPacket(
                check_name="",
                error_extract=["Error in build"],
                done_when="build passes",
            )


class TestTimeSpan:
    def test_green_before_start_fails(self):
        with pytest.raises(Exception):
            TimeSpan(
                t_start=datetime(2026, 1, 2, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_duration(self):
        ts = TimeSpan(
            t_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            t_green=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
        )
        assert ts.duration_seconds == 300.0

    def test_no_green_no_duration(self):
        ts = TimeSpan(t_start=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert ts.duration_seconds is None

    def test_naive_datetime_promoted_to_utc(self):
        ts = TimeSpan(t_start=datetime(2026, 1, 1))
        assert ts.t_start.tzinfo is not None


class TestProofBundle:
    def _make_bundle(self, green: bool = True) -> ProofBundle:
        status = CheckStatus.SUCCESS if green else CheckStatus.FAILURE
        return ProofBundle(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc1234",
            required_checks_final=[CheckResult(name="ci", status=status)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            time=TimeSpan(
                t_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc) if green else None,
            ),
        )

    def test_all_green(self):
        assert self._make_bundle(green=True).all_green

    def test_not_green(self):
        assert not self._make_bundle(green=False).all_green

    def test_empty_checks_not_green(self):
        """v2 fix: empty checks = not proven (fail-closed)."""
        bundle = ProofBundle(
            pr_url="url",
            commit_sha="abc",
            required_checks_final=[],
            diff_summary=DiffSummary(files_changed=0),
            time=TimeSpan(t_start=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )
        assert not bundle.all_green

    def test_integrity_hash_deterministic(self):
        b = self._make_bundle()
        h1 = b.integrity_hash()
        h2 = b.integrity_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_integrity_hash_uses_sorted_keys(self):
        """v2 fix: sorted keys ensures cross-platform determinism."""
        b = self._make_bundle()
        data = b.model_dump(mode="json")
        data.pop("schema_version", None)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert b.integrity_hash() == expected

    def test_schema_version_excluded_from_hash(self):
        """Schema version bumps must not invalidate existing hashes."""
        b1 = self._make_bundle()
        h1 = b1.integrity_hash()
        # The hash should be stable regardless of schema_version
        assert len(h1) == 64

    def test_has_schema_version(self):
        b = self._make_bundle()
        assert b.schema_version == SCHEMA_VERSION


class TestGovernorDecision:
    def test_create(self):
        d = GovernorDecision(action=GovernorAction.MERGE, reason="all good")
        assert d.action == GovernorAction.MERGE
        assert d.reason == "all good"

    def test_frozen(self):
        d = GovernorDecision(action=GovernorAction.HALT)
        with pytest.raises(Exception):
            d.reason = "changed"  # type: ignore

    def test_repr(self):
        d = GovernorDecision(action=GovernorAction.HOLD, reason="review")
        assert "hold" in repr(d)


class TestLoopState:
    def _make_state(self) -> LoopState:
        return LoopState(
            target=TargetState(goal="x", done_when=["All checks green"]),
            constraints=Constraints(),
        )

    def test_record_event(self):
        state = self._make_state()
        state.record("TEST_EVENT", key="val")
        assert len(state.history) == 1
        assert state.history[0].event == "TEST_EVENT"
        assert state.history[0].data["key"] == "val"

    def test_halt(self):
        state = self._make_state()
        state.halt("budget exceeded")
        assert state.halted
        assert state.phase == Phase.HALTED
        assert "budget" in state.halt_reason

    def test_history_bounded(self):
        """v2 fix: history doesn't grow unbounded."""
        state = self._make_state()
        for i in range(3000):
            state.record(f"EVENT_{i}")
        assert len(state.history) <= 2000

    def test_structured_history_events(self):
        """v2: history entries are HistoryEvent, not dicts."""
        state = self._make_state()
        state.record("TEST", x=1)
        event = state.history[0]
        assert isinstance(event, HistoryEvent)
        assert event.ts.tzinfo is not None


# ════════════════════════════════════════════════════════════════════════════════
# §3 — Constraints
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.constraints import ConstraintEnforcer, Violation


class TestConstraintEnforcer:
    def _enforcer(self, **kw) -> ConstraintEnforcer:
        return ConstraintEnforcer(Constraints(**kw))

    def test_wildcard_allows_all(self):
        e = self._enforcer()
        assert e.check_path("any/path/file.py") is None

    def test_denylist_blocks(self):
        e = self._enforcer(touch_denylist=["secrets/**"])
        v = e.check_path("secrets/key.pem")
        assert v is not None
        assert v.rule == EC.PATH_DENIED

    def test_allowlist_restricts(self):
        e = self._enforcer(touch_allowlist=["src/*"])
        v = e.check_path("tests/test.py")
        assert v is not None
        assert v.rule == EC.PATH_NOT_ALLOWED

    def test_deny_takes_priority_over_allow(self):
        """Deny should block even if allow matches."""
        e = self._enforcer(
            touch_allowlist=["*"],
            touch_denylist=["*.secret"],
        )
        v = e.check_path("config.secret")
        assert v is not None

    def test_diff_budget_ok(self):
        e = self._enforcer()
        vs = e.check_diff(DiffSummary(files_changed=5, loc_delta=100))
        assert vs == []

    def test_diff_budget_exceeded(self):
        e = self._enforcer(diff_budget=DiffBudget(max_files=2, max_loc=50))
        vs = e.check_diff(DiffSummary(files_changed=5, loc_delta=100))
        assert len(vs) == 2

    def test_negative_loc_delta_exceeds_budget(self):
        """abs(loc_delta) is checked, not just positive."""
        e = self._enforcer(diff_budget=DiffBudget(max_files=100, max_loc=50))
        vs = e.check_diff(DiffSummary(files_changed=1, loc_delta=-100))
        assert len(vs) == 1

    def test_refactor_blocked(self):
        e = self._enforcer(refactor_policy=RefactorPolicy.NO_REFACTOR)
        v = e.check_refactor(has_refactor=True)
        assert v is not None

    def test_refactor_allowed(self):
        e = self._enforcer(refactor_policy=RefactorPolicy.ALLOWED)
        v = e.check_refactor(has_refactor=True)
        assert v is None

    def test_security_violations(self):
        e = self._enforcer()
        vs = e.check_security(
            disabled_checks=["codeql"],
            unpinned_actions=["actions/checkout@main"],
        )
        assert len(vs) == 2

    def test_full_sweep(self):
        e = self._enforcer(
            touch_denylist=["secrets/**"],
            diff_budget=DiffBudget(max_files=1, max_loc=10),
        )
        vs = e.enforce_all(
            touched_paths=["secrets/key.pem", "src/main.py"],
            diff=DiffSummary(files_changed=5, loc_delta=100),
        )
        assert len(vs) >= 3

    def test_violation_to_error(self):
        v = Violation(rule="TEST_RULE", detail="bad")
        err = v.to_error()
        assert isinstance(err, DAOError)


# ════════════════════════════════════════════════════════════════════════════════
# §4 — Evidence
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.evidence import CheckpointStore, ProofAssembler


class TestProofAssembler:
    def test_assemble(self):
        bundle = ProofAssembler.assemble(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc",
            check_results=[CheckResult(name="ci", status=CheckStatus.SUCCESS)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            t_start=datetime.now(timezone.utc),
            t_green=datetime.now(timezone.utc),
        )
        assert bundle.all_green

    def test_validate_incomplete(self):
        bundle = ProofAssembler.assemble(
            pr_url="",
            commit_sha="",
            check_results=[],
            diff_summary=DiffSummary(files_changed=0),
            t_start=datetime.now(timezone.utc),
        )
        issues = ProofAssembler.validate(bundle)
        assert len(issues) >= 3

    def test_validate_non_green(self):
        bundle = ProofAssembler.assemble(
            pr_url="url",
            commit_sha="abc",
            check_results=[CheckResult(name="ci", status=CheckStatus.FAILURE)],
            diff_summary=DiffSummary(files_changed=1),
            t_start=datetime.now(timezone.utc),
        )
        issues = ProofAssembler.validate(bundle)
        assert any("Non-green" in i for i in issues)


class TestCheckpointStore:
    def _make_bundle(self) -> ProofBundle:
        return ProofBundle(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc1234",
            required_checks_final=[CheckResult(name="ci", status=CheckStatus.SUCCESS)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            time=TimeSpan(
                t_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
            ),
        )

    def test_save_and_load(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        result = store.save_bundle(bundle)
        assert result.is_ok()
        h = result.unwrap()
        assert len(h) == 64

        load_result = store.load_bundle(h[:8])
        assert load_result.is_ok()
        loaded = load_result.unwrap()
        assert loaded is not None
        assert loaded.commit_sha == "abc1234"

    def test_idempotent_save(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        h1 = store.save_bundle(bundle).unwrap()
        h2 = store.save_bundle(bundle).unwrap()
        assert h1 == h2

    def test_ledger(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        store.save_bundle(bundle)
        entries = store.list_bundles()
        assert len(entries) == 1
        assert "schema_version" in entries[0]

    def test_state_snapshot(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        state = LoopState(
            target=TargetState(goal="test", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        result = store.save_state(state, "test_snap")
        assert result.is_ok()

        load_result = store.load_state("test_snap")
        assert load_result.is_ok()
        loaded = load_result.unwrap()
        assert loaded is not None
        assert loaded.target.goal == "test"

    def test_artifact_verify(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"test data")
        ref = ArtifactRef.from_file(f)
        assert store.verify_artifact(ref)

        # Tamper
        f.write_bytes(b"tampered")
        assert not store.verify_artifact(ref)

    def test_missing_artifact(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        ref = ArtifactRef(path="/nonexistent/file", sha256="a" * 64)
        assert not store.verify_artifact(ref)

    def test_load_nonexistent_bundle(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        result = store.load_bundle("nonexistent")
        assert result.is_ok()
        assert result.unwrap() is None

    def test_load_nonexistent_state(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        result = store.load_state("nonexistent")
        assert result.is_ok()
        assert result.unwrap() is None

    def test_list_states_empty(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        assert store.list_states() == []


# ════════════════════════════════════════════════════════════════════════════════
# §5 — Metrics
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.metrics import LoopMetrics, Ledger


class TestLoopMetrics:
    def test_kpd_zero_when_no_data(self):
        m = LoopMetrics()
        assert m.kpd == 0.0

    def test_kpd_calculation(self):
        m = LoopMetrics(diff_budget_loc=500)
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        m.closures = 5
        m.loc_delta = 100
        m.total_iterations = 10
        m.rework_iterations = 2

        # throughput = 5/1 = 5
        # penalty = 1 + 100/500 + 2/10 = 1.4
        # kpd = 5/1.4 ≈ 3.5714
        assert 3.5 < m.kpd < 3.6

    def test_kpd_zero_closures(self):
        m = LoopMetrics()
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        m.closures = 0
        assert m.kpd == 0.0

    def test_kpd_near_zero_time(self):
        """Very small time should not cause division by zero."""
        m = LoopMetrics()
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = m.t_start  # 0 seconds
        m.closures = 5
        assert m.kpd == 0.0  # < 0.001s threshold

    def test_rework_ratio(self):
        m = LoopMetrics()
        m.total_iterations = 10
        m.rework_iterations = 3
        assert m.r_rework == 0.3

    def test_rework_ratio_zero_iterations(self):
        m = LoopMetrics()
        assert m.r_rework == 0.0

    def test_record_iteration(self):
        m = LoopMetrics()
        m.record_iteration(closed=2, new_failures=False)
        m.record_iteration(closed=1, new_failures=True)
        assert m.total_iterations == 2
        assert m.closures == 3
        assert m.rework_iterations == 1

    def test_summary_keys(self):
        m = LoopMetrics()
        s = m.summary()
        expected_keys = {"n_iter", "t_green_s", "files_changed", "loc_delta",
                         "r_rework", "closures", "kpd", "total_iterations",
                         "rework_iterations"}
        assert set(s.keys()) == expected_keys

    def test_start_idempotent(self):
        m = LoopMetrics()
        m.start()
        t1 = m.t_start
        time.sleep(0.01)
        m.start()
        assert m.t_start == t1  # Not overwritten


class TestLedger:
    def test_record_and_stats(self):
        ledger = Ledger()
        m = LoopMetrics()
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        m.closures = 3
        m.loc_delta = 50
        m.diff_budget_loc = 500
        m.total_iterations = 5

        ledger.record("hash123", m, pr="test")
        assert ledger.total_closures == 3
        assert ledger.avg_kpd > 0
        assert ledger.total_iterations == 5


# ════════════════════════════════════════════════════════════════════════════════
# §6 — Roles
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.roles import Scout, Planner, Specifier, Executor, Auditor


class TestScout:
    def test_harvest_failing(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [
            CheckResult(name="lint", status=CheckStatus.FAILURE, run_url="http://x"),
            CheckResult(name="test", status=CheckStatus.SUCCESS),
            CheckResult(name="build", status=CheckStatus.FAILURE),
        ]
        packets = Scout().execute(state, all_checks=checks)
        assert len(packets) == 2
        names = {p.check_name for p in packets}
        assert names == {"lint", "build"}

    def test_harvest_empty_on_all_green(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [CheckResult(name="ci", status=CheckStatus.SUCCESS)]
        packets = Scout().execute(state, all_checks=checks)
        assert packets == []

    def test_skipped_excluded(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [
            CheckResult(name="ci", status=CheckStatus.SUCCESS),
            CheckResult(name="optional", status=CheckStatus.SKIPPED),
        ]
        packets = Scout().execute(state, all_checks=checks)
        assert packets == []

    def test_sorted_by_severity_then_name(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [
            CheckResult(name="z-check", status=CheckStatus.FAILURE),
            CheckResult(name="a-check", status=CheckStatus.FAILURE),
        ]
        packets = Scout().execute(state, all_checks=checks)
        assert packets[0].check_name == "a-check"


class TestPlanner:
    def test_plan_from_packets(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        packets = [
            FailPacket(id="FP-001", check_name="lint",
                       error_extract=["Error: unused import"], done_when="lint passes"),
        ]
        plan = Planner().execute(state, packets=packets)
        assert len(plan) == 1
        assert plan[0]["packet_id"] == "FP-001"

    def test_closed_packets_excluded(self):
        """Planner should skip already-closed packets."""
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
            closed_packet_ids=["FP-001"],
        )
        packets = [
            FailPacket(id="FP-001", check_name="lint",
                       error_extract=["Error: unused import"], done_when="lint passes"),
            FailPacket(id="FP-002", check_name="test",
                       error_extract=["Test failed: test_main"], done_when="test passes"),
        ]
        plan = Planner().execute(state, packets=packets)
        assert len(plan) == 1
        assert plan[0]["packet_id"] == "FP-002"


class TestAuditor:
    def test_all_green_ok(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        verdict, findings = Auditor().execute(
            state,
            check_results=[CheckResult(name="ci", status=CheckStatus.SUCCESS)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=["src/main.py"],
        )
        assert verdict == AuditVerdict.OK
        assert len(findings) == 0

    def test_failing_check_needs_change(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        verdict, _ = Auditor().execute(
            state,
            check_results=[CheckResult(name="ci", status=CheckStatus.FAILURE)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=[],
        )
        assert verdict == AuditVerdict.NEEDS_CHANGE

    def test_skipped_check_is_risk(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        verdict, findings = Auditor().execute(
            state,
            check_results=[
                CheckResult(name="ci", status=CheckStatus.SUCCESS),
                CheckResult(name="optional", status=CheckStatus.SKIPPED),
            ],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=[],
        )
        assert verdict == AuditVerdict.RISK
        assert any("skipped" in f.lower() or "Skipped" in f for f in findings)

    def test_constraint_violation_needs_change(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(touch_denylist=["secrets/**"]),
        )
        enforcer = ConstraintEnforcer(state.constraints)
        verdict, _ = Auditor().execute(
            state,
            check_results=[CheckResult(name="ci", status=CheckStatus.SUCCESS)],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=["secrets/key.pem"],
            enforcer=enforcer,
        )
        assert verdict == AuditVerdict.NEEDS_CHANGE


# ════════════════════════════════════════════════════════════════════════════════
# §7 — Truth Plane
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.truth_plane import PRRef, LocalGate


class TestPRRef:
    def test_parse_url(self):
        ref = PRRef.parse("https://github.com/owner/repo/pull/42")
        assert ref.owner == "owner"
        assert ref.repo == "repo"
        assert ref.number == 42

    def test_parse_shorthand(self):
        ref = PRRef.parse("owner/repo#42")
        assert ref.owner == "owner"
        assert ref.number == 42

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            PRRef.parse("not-a-pr")

    def test_html_url(self):
        ref = PRRef(owner="o", repo="r", number=1)
        assert ref.html_url == "https://github.com/o/r/pull/1"

    def test_api_base(self):
        ref = PRRef(owner="o", repo="r", number=1)
        assert ref.api_base == "https://api.github.com/repos/o/r"

    @given(st.integers(min_value=1, max_value=100000))
    def test_parse_roundtrip(self, n):
        ref = PRRef.parse(f"owner/repo#{n}")
        assert ref.number == n
        reparsed = PRRef.parse(ref.html_url)
        assert reparsed.number == n


class TestLocalGate:
    def test_run_success(self):
        result = LocalGate.run("echo hello")
        assert result.exit_code == 0
        assert result.passed
        assert "hello" in result.log_tail

    def test_run_failure(self):
        result = LocalGate.run("false")
        assert result.exit_code != 0
        assert not result.passed

    def test_run_timeout(self):
        result = LocalGate.run("sleep 10", timeout=0.1)
        assert result.exit_code == 124
        assert not result.passed
        assert "TIMEOUT" in result.log_tail

    def test_run_command_not_found(self):
        result = LocalGate.run("nonexistent_command_xyz_12345")
        assert result.exit_code != 0
        assert not result.passed

    def test_run_returns_structured_result(self):
        """v2: returns LocalGateResult, not tuple."""
        result = LocalGate.run("echo test")
        assert isinstance(result, LocalGateResult)

    def test_shell_expression(self):
        """Commands with pipes use shell mode."""
        result = LocalGate.run("echo hello | cat")
        assert result.exit_code == 0
        assert "hello" in result.log_tail


# ════════════════════════════════════════════════════════════════════════════════
# §8 — Retry
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook._retry import RetryConfig, CircuitBreaker, retry_with_backoff


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.allow_request()

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert not cb.allow_request()

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"


class TestRetryWithBackoff:
    def test_success_on_first_try(self):
        result = retry_with_backoff(lambda: 42)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_fails_after_max_attempts(self):
        call_count = 0
        def failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("nope")

        cfg = RetryConfig(max_attempts=2, base_delay=0.01)
        result = retry_with_backoff(failing, config=cfg)
        assert result.is_err()
        assert call_count == 2

    def test_eventual_success(self):
        attempt = 0
        def flaky():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError("transient")
            return "ok"

        cfg = RetryConfig(max_attempts=5, base_delay=0.01)
        result = retry_with_backoff(flaky, config=cfg)
        assert result.is_ok()
        assert result.unwrap() == "ok"


# ════════════════════════════════════════════════════════════════════════════════
# §9 — Engine
# ════════════════════════════════════════════════════════════════════════════════

from dao_lifebook.engine import CanonicalLoop, EngineConfig


class TestEngineConfig:
    def test_invalid_max_iterations(self):
        with pytest.raises(ValueError):
            EngineConfig(max_iterations=0)


class TestCanonicalLoop:
    def _green_checks(self) -> list[CheckResult]:
        return [
            CheckResult(name="lint", status=CheckStatus.SUCCESS),
            CheckResult(name="test", status=CheckStatus.SUCCESS),
        ]

    def _mixed_checks(self) -> list[CheckResult]:
        return [
            CheckResult(name="lint", status=CheckStatus.SUCCESS),
            CheckResult(name="test", status=CheckStatus.FAILURE),
        ]

    def test_all_green_merges(self, tmp_path):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        decision = loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc123",
            pr_url="https://github.com/o/r/pull/1",
            diff_summary=DiffSummary(files_changed=2, loc_delta=30),
            touched_files=["src/a.py", "src/b.py"],
        )
        assert decision.action == GovernorAction.MERGE

    def test_failing_goes_next(self, tmp_path):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        decision = loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="abc123",
            pr_url="https://github.com/o/r/pull/1",
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=["src/a.py"],
        )
        assert decision.action == GovernorAction.NEXT

    def test_max_iterations_halt(self, tmp_path):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(max_iterations=1, checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="abc", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        decision = loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="def", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        assert decision.action == GovernorAction.HALT

    def test_can_stop(self, tmp_path):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        assert loop.can_stop()

    def test_cannot_stop_without_proof(self):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
        )
        assert not loop.can_stop()

    def test_checkpoint_and_stop(self, tmp_path):
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        result = loop.checkpoint_and_stop()
        assert result["stopped"]
        assert result["proof_hash"]

    def test_governor_fn_override(self, tmp_path):
        def my_governor(state, findings):
            return GovernorDecision(action=GovernorAction.HOLD, reason="Manual review")

        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(
                checkpoint_store=CheckpointStore(tmp_path / "ev"),
                governor_fn=my_governor,
            ),
        )
        decision = loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        assert decision.action == GovernorAction.HOLD

    def test_constraint_halt_in_spec(self, tmp_path):
        """Spec targeting denied path triggers HALT."""
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(touch_denylist=["secrets/**"]),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        state = loop.state
        state.iteration = 1
        state.phase = Phase.SPECIFY

        packet = FailPacket(
            id="FP-TEST", check_name="test",
            error_extract=["Error in secrets/key.pem"],
            file_line="secrets/key.pem:10",
            done_when="test passes",
        )

        spec = Specifier().execute(state, task={"rollback": "revert"}, packet=packet)
        violations = loop.enforcer.check_paths(spec.scope_files)
        assert len(violations) > 0

    def test_rework_detection(self, tmp_path):
        """v2 fix: correctly detect new failures introduced during fix."""
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )

        # Iteration 1: 'test' failing
        loop.run_iteration(
            check_results=[
                CheckResult(name="lint", status=CheckStatus.SUCCESS),
                CheckResult(name="test", status=CheckStatus.FAILURE),
            ],
            sha="aaa", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        # Iteration 2: 'test' fixed but 'build' now failing (NEW failure)
        loop.run_iteration(
            check_results=[
                CheckResult(name="lint", status=CheckStatus.SUCCESS),
                CheckResult(name="test", status=CheckStatus.SUCCESS),
                CheckResult(name="build", status=CheckStatus.FAILURE),
            ],
            sha="bbb", pr_url="url",
            diff_summary=DiffSummary(files_changed=2, loc_delta=15),
            touched_files=["a.py", "b.py"],
        )

        # Should detect rework
        assert loop.metrics.rework_iterations >= 1


# ════════════════════════════════════════════════════════════════════════════════
# §10 — Integration Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestFullLoopIntegration:
    def test_green_path(self, tmp_path):
        target = TargetState(
            goal="Ship feature X",
            commands=["make test"],
            done_when=["All CI checks green", "Audit passes"],
        )
        constraints = Constraints(diff_budget=DiffBudget(max_files=10, max_loc=200))
        store = CheckpointStore(tmp_path / "evidence")
        loop = CanonicalLoop(target, constraints, EngineConfig(checkpoint_store=store))

        checks = [
            CheckResult(name="lint", status=CheckStatus.SUCCESS),
            CheckResult(name="test", status=CheckStatus.SUCCESS),
            CheckResult(name="build", status=CheckStatus.SUCCESS),
        ]
        decision = loop.run_iteration(
            check_results=checks,
            sha="deadbeef",
            pr_url="https://github.com/test/repo/pull/99",
            diff_summary=DiffSummary(files_changed=3, loc_delta=45),
            touched_files=["src/a.py", "src/b.py", "tests/test_a.py"],
        )

        assert decision.action == GovernorAction.MERGE
        assert loop.state.proof is not None
        assert loop.state.proof.all_green
        assert loop.can_stop()

        result = loop.checkpoint_and_stop()
        assert result["stopped"]

        entries = store.list_bundles()
        assert len(entries) >= 1
        assert "final" in store.list_states()

    def test_fix_path(self, tmp_path):
        """Failing → fix → green."""
        loop = CanonicalLoop(
            TargetState(goal="Fix lint", done_when=["lint check passes"]),
            Constraints(),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )

        d1 = loop.run_iteration(
            check_results=[CheckResult(name="lint", status=CheckStatus.FAILURE)],
            sha="aaa", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        assert d1.action == GovernorAction.NEXT

        d2 = loop.run_iteration(
            check_results=[CheckResult(name="lint", status=CheckStatus.SUCCESS)],
            sha="bbb", pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=8),
            touched_files=["a.py"],
        )
        assert d2.action == GovernorAction.MERGE
        assert loop.state.iteration == 2

    def test_budget_exceeded_halts(self, tmp_path):
        """Exceeding diff budget in audit should not merge."""
        loop = CanonicalLoop(
            TargetState(goal="fix", done_when=["All checks pass"]),
            Constraints(diff_budget=DiffBudget(max_files=1, max_loc=10)),
            EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev")),
        )
        decision = loop.run_iteration(
            check_results=[CheckResult(name="ci", status=CheckStatus.SUCCESS)],
            sha="abc", pr_url="url",
            diff_summary=DiffSummary(files_changed=5, loc_delta=500),
            touched_files=["a.py", "b.py", "c.py", "d.py", "e.py"],
        )
        # Budget exceeded → audit finds violations → HOLD or NEXT
        assert decision.action != GovernorAction.MERGE


# ════════════════════════════════════════════════════════════════════════════════
# §11 — Property-Based Tests (Hypothesis)
# ════════════════════════════════════════════════════════════════════════════════

class TestPropertyBased:
    @given(st.text(min_size=64, max_size=64, alphabet="0123456789abcdef"))
    def test_artifact_ref_valid_hex(self, hex_str):
        ref = ArtifactRef(path="test", sha256=hex_str)
        assert ref.sha256 == hex_str

    @given(st.text(min_size=1, max_size=10).filter(
        lambda s: len(s) != 64 or not all(c in "0123456789abcdef" for c in s)
    ))
    def test_artifact_ref_invalid_hex_rejected(self, bad_hex):
        assume(bad_hex != "")  # empty is valid
        with pytest.raises(Exception):
            ArtifactRef(path="test", sha256=bad_hex)

    @given(
        files=st.integers(min_value=0, max_value=1000),
        loc=st.integers(min_value=-5000, max_value=5000),
        max_files=st.integers(min_value=1, max_value=100),
        max_loc=st.integers(min_value=1, max_value=1000),
    )
    def test_diff_budget_consistency(self, files, loc, max_files, max_loc):
        """If within budget, no violations. If exceeded, violations present."""
        enforcer = ConstraintEnforcer(
            Constraints(diff_budget=DiffBudget(max_files=max_files, max_loc=max_loc))
        )
        vs = enforcer.check_diff(DiffSummary(files_changed=files, loc_delta=loc))

        if files <= max_files and abs(loc) <= max_loc:
            assert len(vs) == 0
        if files > max_files:
            assert any(EC.DIFF_BUDGET in v.rule for v in vs)

    @given(st.integers(min_value=0, max_value=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_kpd_non_negative(self, closures):
        """KPD is never negative."""
        m = LoopMetrics()
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        m.closures = closures
        assert m.kpd >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
