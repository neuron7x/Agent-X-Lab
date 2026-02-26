"""
DAO-LIFEBOOK — Test Suite.

Tests the actual functionality: models, constraints, evidence, engine, metrics.
No mocks for core logic — real execution paths.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# ─── Model Tests ──────────────────────────────────────────────────────────────

from dao_lifebook.models import (
    ArtifactRef,
    AuditVerdict,
    CheckResult,
    CheckStatus,
    Constraints,
    DiffBudget,
    DiffSummary,
    EditInstruction,
    EvidencePointer,
    FailPacket,
    LocalGateResult,
    LoopState,
    Phase,
    ProofBundle,
    RefactorPolicy,
    SecurityPolicy,
    Spec,
    TargetState,
    TimeSpan,
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


class TestArtifactRef:
    def test_valid_hash(self):
        ref = ArtifactRef(path="a.txt", sha256="a" * 64)
        assert ref.sha256 == "a" * 64

    def test_invalid_hash_rejects(self):
        with pytest.raises(Exception):
            ArtifactRef(path="a.txt", sha256="short")

    def test_empty_hash_ok(self):
        ref = ArtifactRef(path="a.txt", sha256="")
        assert ref.sha256 == ""

    def test_from_file(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        ref = ArtifactRef.from_file(f)
        assert ref.sha256
        assert len(ref.sha256) == 64


class TestTargetState:
    def test_valid(self):
        ts = TargetState(
            goal="Fix CI",
            done_when=["All checks green"],
        )
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


class TestConstraints:
    def test_defaults(self):
        c = Constraints()
        assert c.touch_allowlist == ["*"]
        assert c.diff_budget.max_files == 20
        assert c.refactor_policy == RefactorPolicy.NO_REFACTOR
        assert c.security_policy.no_disable_security_checks is True


class TestFailPacket:
    def test_valid(self):
        fp = FailPacket(
            check_name="lint",
            error_extract=["Error: unused import at line 42"],
            done_when="lint check passes",
        )
        assert fp.severity == 0

    def test_insufficient_signal(self):
        with pytest.raises(Exception):
            FailPacket(
                check_name="lint",
                error_extract=["x"],
                done_when="fix",
            )


class TestProofBundle:
    def _make_bundle(self, green: bool = True) -> ProofBundle:
        status = CheckStatus.SUCCESS if green else CheckStatus.FAILURE
        return ProofBundle(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc1234",
            required_checks_final=[
                CheckResult(name="ci", status=status),
            ],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            time=TimeSpan(
                t_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc) if green else None,
            ),
        )

    def test_all_green(self):
        b = self._make_bundle(green=True)
        assert b.all_green

    def test_not_green(self):
        b = self._make_bundle(green=False)
        assert not b.all_green

    def test_integrity_hash_deterministic(self):
        b = self._make_bundle()
        h1 = b.integrity_hash()
        h2 = b.integrity_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_duration(self):
        b = self._make_bundle()
        assert b.time.duration_seconds == 300.0


class TestTimeSpan:
    def test_green_before_start_fails(self):
        with pytest.raises(Exception):
            TimeSpan(
                t_start=datetime(2026, 1, 2, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )


class TestLoopState:
    def test_record(self):
        state = LoopState(
            target=TargetState(goal="x", done_when=["All checks green"]),
            constraints=Constraints(),
        )
        state.record("TEST_EVENT", key="val")
        assert len(state.history) == 1
        assert state.history[0]["event"] == "TEST_EVENT"

    def test_halt(self):
        state = LoopState(
            target=TargetState(goal="x", done_when=["All checks green"]),
            constraints=Constraints(),
        )
        state.halt("budget exceeded")
        assert state.halted
        assert state.phase == Phase.HALTED
        assert "budget" in state.halt_reason


# ─── Constraint Tests ─────────────────────────────────────────────────────────

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
        assert v.rule == "touch_denylist"

    def test_allowlist_restricts(self):
        e = self._enforcer(touch_allowlist=["src/*"])
        v = e.check_path("tests/test.py")
        assert v is not None
        assert v.rule == "touch_allowlist"

    def test_diff_budget_ok(self):
        e = self._enforcer()
        vs = e.check_diff(DiffSummary(files_changed=5, loc_delta=100))
        assert vs == []

    def test_diff_budget_exceeded(self):
        e = self._enforcer(
            diff_budget=DiffBudget(max_files=2, max_loc=50)
        )
        vs = e.check_diff(DiffSummary(files_changed=5, loc_delta=100))
        assert len(vs) == 2

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
        assert len(vs) >= 3  # deny + files + loc


# ─── Evidence Tests ───────────────────────────────────────────────────────────

from dao_lifebook.evidence import CheckpointStore, ProofAssembler


class TestProofAssembler:
    def test_assemble(self):
        bundle = ProofAssembler.assemble(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc",
            check_results=[
                CheckResult(name="ci", status=CheckStatus.SUCCESS),
            ],
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
        assert len(issues) >= 3  # missing pr, sha, checks, t_green


class TestCheckpointStore:
    def _make_bundle(self) -> ProofBundle:
        return ProofBundle(
            pr_url="https://github.com/o/r/pull/1",
            commit_sha="abc1234",
            required_checks_final=[
                CheckResult(name="ci", status=CheckStatus.SUCCESS),
            ],
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            time=TimeSpan(
                t_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                t_green=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
            ),
        )

    def test_save_and_load(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        h = store.save_bundle(bundle)
        assert len(h) == 64

        loaded = store.load_bundle(h[:8])
        assert loaded is not None
        assert loaded.commit_sha == "abc1234"

    def test_idempotent_save(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        h1 = store.save_bundle(bundle)
        h2 = store.save_bundle(bundle)
        assert h1 == h2

    def test_ledger(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        bundle = self._make_bundle()
        store.save_bundle(bundle)
        entries = store.list_bundles()
        assert len(entries) == 1

    def test_state_snapshot(self, tmp_path):
        store = CheckpointStore(tmp_path / "evidence")
        state = LoopState(
            target=TargetState(goal="test", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        store.save_state(state, "test_snap")
        loaded = store.load_state("test_snap")
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


# ─── Metrics Tests ────────────────────────────────────────────────────────────

from dao_lifebook.metrics import LoopMetrics, Ledger


class TestLoopMetrics:
    def test_kpd_zero_when_no_data(self):
        m = LoopMetrics()
        assert m.kpd == 0.0

    def test_kpd_calculation(self):
        m = LoopMetrics(diff_budget_loc=500)
        m.t_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        m.t_green = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)  # 1 hour
        m.closures = 5
        m.loc_delta = 100
        m.total_iterations = 10
        m.rework_iterations = 2

        # throughput = 5/1 = 5
        # penalty = 1 + 100/500 + 2/10 = 1 + 0.2 + 0.2 = 1.4
        # kpd = 5 / 1.4 ≈ 3.5714
        assert 3.5 < m.kpd < 3.6

    def test_rework_ratio(self):
        m = LoopMetrics()
        m.total_iterations = 10
        m.rework_iterations = 3
        assert m.r_rework == 0.3

    def test_record_iteration(self):
        m = LoopMetrics()
        m.record_iteration(closed=2, new_failures=False)
        m.record_iteration(closed=1, new_failures=True)
        assert m.total_iterations == 2
        assert m.closures == 3
        assert m.rework_iterations == 1


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


# ─── Role Tests ───────────────────────────────────────────────────────────────

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
        scout = Scout()
        packets = scout.execute(state, all_checks=checks)
        assert len(packets) == 2
        assert packets[0].check_name in ("lint", "build")


class TestPlanner:
    def test_plan_from_packets(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        packets = [
            FailPacket(
                id="FP-001",
                check_name="lint",
                error_extract=["Error: unused import"],
                done_when="lint passes",
            ),
        ]
        planner = Planner()
        plan = planner.execute(state, packets=packets)
        assert len(plan) == 1
        assert plan[0]["packet_id"] == "FP-001"


class TestAuditor:
    def test_all_green_ok(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [CheckResult(name="ci", status=CheckStatus.SUCCESS)]
        diff = DiffSummary(files_changed=1, loc_delta=10)

        auditor = Auditor()
        verdict, findings = auditor.execute(
            state,
            check_results=checks,
            diff_summary=diff,
            touched_files=["src/main.py"],
        )
        assert verdict == AuditVerdict.OK
        assert len(findings) == 0

    def test_failing_check_needs_change(self):
        state = LoopState(
            target=TargetState(goal="fix", done_when=["All checks pass"]),
            constraints=Constraints(),
        )
        checks = [CheckResult(name="ci", status=CheckStatus.FAILURE)]
        diff = DiffSummary(files_changed=1, loc_delta=10)

        auditor = Auditor()
        verdict, _ = auditor.execute(
            state,
            check_results=checks,
            diff_summary=diff,
            touched_files=[],
        )
        assert verdict == AuditVerdict.NEEDS_CHANGE


# ─── Engine Tests ─────────────────────────────────────────────────────────────

from dao_lifebook.engine import CanonicalLoop, EngineConfig, GovernorDecision


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
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()
        config = EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev"))

        loop = CanonicalLoop(target, constraints, config)

        decision = loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc123",
            pr_url="https://github.com/o/r/pull/1",
            diff_summary=DiffSummary(files_changed=2, loc_delta=30),
            touched_files=["src/a.py", "src/b.py"],
        )

        assert decision.action == GovernorDecision.MERGE

    def test_failing_goes_next(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()
        config = EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev"))

        loop = CanonicalLoop(target, constraints, config)

        decision = loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="abc123",
            pr_url="https://github.com/o/r/pull/1",
            diff_summary=DiffSummary(files_changed=1, loc_delta=10),
            touched_files=["src/a.py"],
        )

        assert decision.action == GovernorDecision.NEXT

    def test_max_iterations_halt(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()
        config = EngineConfig(
            max_iterations=1,
            checkpoint_store=CheckpointStore(tmp_path / "ev"),
        )

        loop = CanonicalLoop(target, constraints, config)

        # First iteration OK
        loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="abc",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        # Second exceeds max
        decision = loop.run_iteration(
            check_results=self._mixed_checks(),
            sha="def",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        assert decision.action == GovernorDecision.HALT

    def test_can_stop(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()
        config = EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev"))

        loop = CanonicalLoop(target, constraints, config)

        loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        assert loop.can_stop()

    def test_checkpoint_and_stop(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()
        config = EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev"))

        loop = CanonicalLoop(target, constraints, config)

        loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        result = loop.checkpoint_and_stop()
        assert result["stopped"]
        assert result["proof_hash"]
        assert result["metrics"]["kpd"] >= 0

    def test_governor_fn_override(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints()

        def my_governor(state, findings):
            return GovernorDecision(GovernorDecision.HOLD, "Manual review")

        config = EngineConfig(
            checkpoint_store=CheckpointStore(tmp_path / "ev"),
            governor_fn=my_governor,
        )

        loop = CanonicalLoop(target, constraints, config)
        decision = loop.run_iteration(
            check_results=self._green_checks(),
            sha="abc",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )

        assert decision.action == GovernorDecision.HOLD
        assert decision.reason == "Manual review"

    def test_constraint_halt_in_spec(self, tmp_path):
        target = TargetState(goal="fix", done_when=["All checks pass"])
        constraints = Constraints(touch_denylist=["secrets/**"])
        config = EngineConfig(checkpoint_store=CheckpointStore(tmp_path / "ev"))

        loop = CanonicalLoop(target, constraints, config)

        # Manually trigger with a packet that has file_line in denied path
        state = loop.state
        state.iteration = 1
        state.phase = Phase.SPECIFY

        packet = FailPacket(
            id="FP-TEST",
            check_name="test",
            error_extract=["Error in secrets/key.pem"],
            file_line="secrets/key.pem:10",
            done_when="test passes",
        )

        from dao_lifebook.roles import Specifier
        spec = Specifier().execute(state, task={"rollback": "revert"}, packet=packet)

        # Spec targets a denied path
        from dao_lifebook.constraints import ConstraintEnforcer
        enforcer = ConstraintEnforcer(constraints)
        violations = enforcer.check_paths(spec.scope_files)
        assert len(violations) > 0


# ─── Truth Plane Tests ────────────────────────────────────────────────────────

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


class TestLocalGate:
    def test_run_success(self):
        code, output = LocalGate.run("echo hello")
        assert code == 0
        assert "hello" in output

    def test_run_failure(self):
        code, _ = LocalGate.run("false")
        assert code != 0

    def test_run_timeout(self):
        code, output = LocalGate.run("sleep 10", timeout=0.1)
        assert code == 124
        assert "TIMEOUT" in output


# ─── Integration Test ─────────────────────────────────────────────────────────

class TestFullLoopIntegration:
    """End-to-end: construct → iterate → prove → checkpoint."""

    def test_green_path(self, tmp_path):
        target = TargetState(
            goal="Ship feature X",
            commands=["make test"],
            done_when=["All CI checks green", "Audit passes"],
        )
        constraints = Constraints(
            diff_budget=DiffBudget(max_files=10, max_loc=200),
        )
        store = CheckpointStore(tmp_path / "evidence")
        config = EngineConfig(checkpoint_store=store)

        loop = CanonicalLoop(target, constraints, config)

        # Simulate: all green from the start
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

        # Should merge
        assert decision.action == GovernorDecision.MERGE

        # Proof should exist
        assert loop.state.proof is not None
        assert loop.state.proof.all_green

        # Can stop
        assert loop.can_stop()

        # Checkpoint
        result = loop.checkpoint_and_stop()
        assert result["stopped"]

        # Verify ledger
        entries = store.list_bundles()
        assert len(entries) >= 1

        # Verify state snapshot
        states = store.list_states()
        assert "final" in states

    def test_fix_path(self, tmp_path):
        """Simulate: failing → fix → green."""
        target = TargetState(
            goal="Fix lint",
            done_when=["lint check passes"],
        )
        constraints = Constraints()
        store = CheckpointStore(tmp_path / "evidence")
        config = EngineConfig(checkpoint_store=store)

        loop = CanonicalLoop(target, constraints, config)

        # Iteration 1: failing
        d1 = loop.run_iteration(
            check_results=[
                CheckResult(name="lint", status=CheckStatus.FAILURE),
            ],
            sha="aaa",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=5),
            touched_files=["a.py"],
        )
        assert d1.action == GovernorDecision.NEXT

        # Iteration 2: green
        d2 = loop.run_iteration(
            check_results=[
                CheckResult(name="lint", status=CheckStatus.SUCCESS),
            ],
            sha="bbb",
            pr_url="url",
            diff_summary=DiffSummary(files_changed=1, loc_delta=8),
            touched_files=["a.py"],
        )
        assert d2.action == GovernorDecision.MERGE
        assert loop.state.iteration == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
