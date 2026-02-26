"""
DAO-LIFEBOOK — Canonical Loop Engine (§5).

State machine: OBSERVE → PACKETIZE → PLAN → SPECIFY → EXECUTE → PROVE → AUDIT → DECIDE.
Each phase transition is explicit, logged, and checkpointed.

Human Governor retains all DECIDE authority.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from .models import (
    AuditVerdict,
    CheckResult,
    CheckStatus,
    Constraints,
    DiffSummary,
    FailPacket,
    LoopState,
    Phase,
    ProofBundle,
    Spec,
    TargetState,
)
from .constraints import ConstraintEnforcer
from .evidence import CheckpointStore, ProofAssembler
from .metrics import LoopMetrics
from .roles import Auditor, Executor, Planner, Scout, Specifier

logger = logging.getLogger("dao.engine")


class GovernorDecision:
    """
    Governor (human) decision interface.

    The engine NEVER auto-merges. It proposes; Governor decides.
    """

    __slots__ = ("action", "reason")

    MERGE = "merge"
    HOLD = "hold"
    NEXT = "next_loop"
    HALT = "halt"

    def __init__(self, action: str, reason: str = "") -> None:
        if action not in (self.MERGE, self.HOLD, self.NEXT, self.HALT):
            raise ValueError(f"Invalid governor action: {action!r}")
        self.action = action
        self.reason = reason

    def __repr__(self) -> str:
        return f"GovernorDecision({self.action!r}, {self.reason!r})"


class EngineConfig:
    """Runtime configuration for the loop engine."""

    __slots__ = (
        "max_iterations",
        "auto_checkpoint",
        "checkpoint_store",
        "governor_fn",
        "apply_fn",
    )

    def __init__(
        self,
        *,
        max_iterations: int = 50,
        auto_checkpoint: bool = True,
        checkpoint_store: CheckpointStore | None = None,
        governor_fn: Callable[[LoopState, list[str]], GovernorDecision] | None = None,
        apply_fn: Callable[[Spec], None] | None = None,
    ) -> None:
        self.max_iterations = max_iterations
        self.auto_checkpoint = auto_checkpoint
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.governor_fn = governor_fn
        self.apply_fn = apply_fn


class CanonicalLoop:
    """
    The canonical loop algorithm (§5).

    This is the heart of DAO-LIFEBOOK. It orchestrates roles through
    phases, enforces constraints, and produces evidence.
    """

    __slots__ = (
        "_state", "_config", "_metrics", "_enforcer",
        "_scout", "_planner", "_specifier", "_executor", "_auditor",
    )

    def __init__(
        self,
        target: TargetState,
        constraints: Constraints,
        config: EngineConfig | None = None,
    ) -> None:
        self._config = config or EngineConfig()
        self._state = LoopState(target=target, constraints=constraints)
        self._metrics = LoopMetrics(diff_budget_loc=constraints.diff_budget.max_loc)
        self._enforcer = ConstraintEnforcer(constraints)

        # Instantiate roles
        self._scout = Scout()
        self._planner = Planner()
        self._specifier = Specifier()
        self._executor = Executor()
        self._auditor = Auditor()

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics

    # ── Phase Implementations ─────────────────────────────────────────────

    def phase_observe(
        self,
        check_results: list[CheckResult],
        sha: str = "",
    ) -> list[CheckResult]:
        """Phase A — Ground truth snapshot."""
        self._state.phase = Phase.OBSERVE
        self._metrics.start()

        # Filter to required checks
        target = self._state.target
        if isinstance(target.required_checks, list):
            required_names = target.required_checks
            required = [c for c in check_results if c.name in set(required_names)]
        else:
            required = [c for c in check_results if c.status != CheckStatus.SKIPPED]

        self._state.record(
            "OBSERVED",
            sha=sha,
            total_checks=len(check_results),
            required_checks=len(required),
            green=[c.name for c in required if c.status.is_green],
            failing=[c.name for c in required if not c.status.is_green],
        )

        logger.info(
            "Observed %d checks (%d required, %d green)",
            len(check_results),
            len(required),
            sum(1 for c in required if c.status.is_green),
        )
        return required

    def phase_packetize(
        self,
        required_checks: list[CheckResult],
    ) -> list[FailPacket]:
        """Phase B — Convert failures to packets."""
        self._state.phase = Phase.PACKETIZE

        packets = self._scout.execute(
            self._state,
            all_checks=required_checks,
        )

        self._state.active_packets = packets
        return packets

    def phase_plan(
        self,
        packets: list[FailPacket],
    ) -> list[dict[str, Any]]:
        """Phase C — Build task graph."""
        self._state.phase = Phase.PLAN

        plan = self._planner.execute(
            self._state,
            packets=packets,
        )
        return plan

    def phase_specify(
        self,
        task: dict[str, Any],
        packet: FailPacket,
    ) -> Spec:
        """Phase D — Compile plan into executable spec."""
        self._state.phase = Phase.SPECIFY

        spec = self._specifier.execute(
            self._state,
            task=task,
            packet=packet,
        )
        self._state.current_spec = spec
        return spec

    def phase_execute(self, spec: Spec) -> dict[str, Any]:
        """Phase E — Apply minimal patch."""
        self._state.phase = Phase.EXECUTE

        result = self._executor.execute(
            self._state,
            spec=spec,
            apply_fn=self._config.apply_fn,
        )
        return result

    def phase_prove(
        self,
        check_results: list[CheckResult],
    ) -> bool:
        """
        Phase F — CI as oracle.

        Returns True if all required checks are green.
        """
        self._state.phase = Phase.PROVE

        target = self._state.target
        if isinstance(target.required_checks, list):
            req_names = set(target.required_checks)
            required = [c for c in check_results if c.name in req_names]
        else:
            required = [c for c in check_results if c.status != CheckStatus.SKIPPED]

        all_green = all(c.status.is_green for c in required)

        if all_green:
            self._metrics.mark_green()
            self._metrics.n_iter = self._state.iteration

        self._state.record(
            "PROVE_RESULT",
            all_green=all_green,
            results={c.name: c.status.value for c in required},
        )
        return all_green

    def phase_audit(
        self,
        check_results: list[CheckResult],
        diff_summary: DiffSummary,
        touched_files: list[str],
    ) -> tuple[AuditVerdict, list[str]]:
        """Phase G — Post-green semantic correctness."""
        self._state.phase = Phase.AUDIT

        verdict, findings = self._auditor.execute(
            self._state,
            check_results=check_results,
            diff_summary=diff_summary,
            touched_files=touched_files,
            enforcer=self._enforcer,
        )

        self._state.audit_verdict = verdict
        self._metrics.record_diff(diff_summary.files_changed, diff_summary.loc_delta)
        return verdict, findings

    def phase_decide(
        self,
        *,
        check_results: list[CheckResult],
        diff_summary: DiffSummary,
        sha: str,
        pr_url: str,
        audit_findings: list[str],
    ) -> GovernorDecision:
        """
        Phase H — Governor decision.

        If governor_fn is provided, defer to it.
        Otherwise, return a proposed decision based on state.
        """
        self._state.phase = Phase.DECIDE

        # Build proof bundle
        proof = ProofAssembler.assemble(
            pr_url=pr_url,
            commit_sha=sha,
            check_results=check_results,
            diff_summary=diff_summary,
            t_start=self._metrics.t_start or datetime.now(timezone.utc),
            t_green=self._metrics.t_green,
        )
        self._state.proof = proof

        # Checkpoint
        if self._config.auto_checkpoint:
            self._config.checkpoint_store.save_bundle(proof)
            self._config.checkpoint_store.save_state(self._state)

        # Determine decision
        all_green = proof.all_green
        audit_ok = self._state.audit_verdict == AuditVerdict.OK

        if self._config.governor_fn:
            decision = self._config.governor_fn(self._state, audit_findings)
        elif all_green and audit_ok:
            decision = GovernorDecision(
                GovernorDecision.MERGE,
                "All checks green + audit OK",
            )
        elif all_green and self._state.audit_verdict == AuditVerdict.RISK:
            decision = GovernorDecision(
                GovernorDecision.HOLD,
                f"Green but audit RISK: {audit_findings}",
            )
        else:
            decision = GovernorDecision(
                GovernorDecision.NEXT,
                "Not all conditions met for merge",
            )

        self._state.record(
            "DECISION",
            action=decision.action,
            reason=decision.reason,
            all_green=all_green,
            audit=self._state.audit_verdict.value if self._state.audit_verdict else None,
        )

        return decision

    # ── Full Iteration ────────────────────────────────────────────────────

    def run_iteration(
        self,
        *,
        check_results: list[CheckResult],
        sha: str,
        pr_url: str,
        diff_summary: DiffSummary,
        touched_files: list[str],
    ) -> GovernorDecision:
        """
        Run one complete iteration of the canonical loop.

        This is the primary entry point for automation.
        Handles all phases A through H.
        """
        self._state.iteration += 1

        if self._state.iteration > self._config.max_iterations:
            self._state.halt(
                f"Max iterations ({self._config.max_iterations}) exceeded"
            )
            return GovernorDecision(
                GovernorDecision.HALT,
                self._state.halt_reason,
            )

        # A: Observe
        required = self.phase_observe(check_results, sha)

        # B: Packetize
        packets = self.phase_packetize(required)

        if not packets:
            # All green — skip to audit
            verdict, findings = self.phase_audit(
                check_results=required,
                diff_summary=diff_summary,
                touched_files=touched_files,
            )
            return self.phase_decide(
                check_results=required,
                diff_summary=diff_summary,
                sha=sha,
                pr_url=pr_url,
                audit_findings=findings,
            )

        # C: Plan
        plan = self.phase_plan(packets)

        # Track new failures for rework metric
        prev_checks = {p.check_name for p in self._state.active_packets}

        # D+E: Specify and Execute for each task
        for task in plan:
            pid = task["packet_id"]
            packet = next((p for p in packets if p.id == pid), None)
            if packet is None:
                continue

            spec = self.phase_specify(task, packet)

            # Constraint pre-check on scope
            scope_violations = self._enforcer.check_paths(spec.scope_files)
            if scope_violations:
                self._state.halt(
                    f"Constraint violation in spec scope: "
                    f"{[v.detail for v in scope_violations]}"
                )
                return GovernorDecision(
                    GovernorDecision.HALT,
                    self._state.halt_reason,
                )

            exec_result = self.phase_execute(spec)

            if exec_result["errors"]:
                logger.warning(
                    "Execution errors for %s: %s",
                    pid, exec_result["errors"],
                )

        # F: Prove (requires re-observation — caller must re-fetch CI)
        all_green = self.phase_prove(check_results)

        # Track rework
        new_failing = {p.check_name for p in packets} - prev_checks
        self._metrics.record_iteration(
            closed=len(prev_checks - {p.check_name for p in packets}),
            new_failures=bool(new_failing),
        )

        if not all_green:
            return GovernorDecision(
                GovernorDecision.NEXT,
                f"Still failing: {[p.check_name for p in packets]}",
            )

        # G: Audit
        verdict, findings = self.phase_audit(
            check_results=check_results,
            diff_summary=diff_summary,
            touched_files=touched_files,
        )

        # H: Decide
        return self.phase_decide(
            check_results=check_results,
            diff_summary=diff_summary,
            sha=sha,
            pr_url=pr_url,
            audit_findings=findings,
        )

    # ── Stop Rule (§6.2) ─────────────────────────────────────────────────

    def can_stop(self) -> bool:
        """
        §6.2 STOP RULE:
        If PASS_CONTRACT is met and proof bundle captured → MAY stop.
        """
        if self._state.proof is None:
            return False
        if not self._state.proof.all_green:
            return False
        if self._state.audit_verdict != AuditVerdict.OK:
            return False
        return True

    def checkpoint_and_stop(self) -> dict[str, Any]:
        """
        §6.3 CHECKPOINT RULE:
        Every closure produces a PROOF_BUNDLE so tomorrow starts from verified reality.
        """
        if not self.can_stop():
            return {"stopped": False, "reason": "Cannot stop: contract not met"}

        proof = self._state.proof
        assert proof is not None

        h = self._config.checkpoint_store.save_bundle(proof)
        self._config.checkpoint_store.save_state(self._state, "final")

        return {
            "stopped": True,
            "proof_hash": h,
            "metrics": self._metrics.summary(),
            "state_snapshot": "final",
        }
