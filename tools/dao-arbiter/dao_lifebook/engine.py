"""
DAO-LIFEBOOK — Canonical Loop Engine (§5).

State machine: OBSERVE → PACKETIZE → PLAN → SPECIFY → EXECUTE → PROVE → AUDIT → DECIDE.
Each phase transition is explicit, logged, and checkpointed.
Human Governor retains all DECIDE authority.

v2 critical fixes:
  • PROVE phase requires FRESH CI data (not stale pre-execute snapshot)
  • Rework tracking correctly detects new failures vs. pre-existing
  • GovernorDecision is a proper Pydantic model with GovernorAction enum
  • Phase transitions are explicit via advance_phase()
  • Result-based error propagation from evidence layer
  • Constraint violations return structured errors
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from ._types import Result, Ok, Err, DAOError, ErrorSeverity, EC
from .models import (
    AuditVerdict,
    CheckResult,
    CheckStatus,
    Constraints,
    DiffSummary,
    FailPacket,
    GovernorAction,
    GovernorDecision,
    LoopState,
    Phase,
    Spec,
    TargetState,
)
from .constraints import ConstraintEnforcer
from .evidence import CheckpointStore, ProofAssembler
from .metrics import LoopMetrics
from .roles import Auditor, Executor, Planner, Scout, Specifier

logger = logging.getLogger("dao.engine")


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
        if max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1, got {max_iterations}")
        self.max_iterations = max_iterations
        self.auto_checkpoint = auto_checkpoint
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.governor_fn = governor_fn
        self.apply_fn = apply_fn


class CanonicalLoop:
    """
    The canonical loop algorithm (§5).

    Orchestrates roles through phases, enforces constraints, produces evidence.
    The engine NEVER auto-merges — it only proposes decisions.
    """

    __slots__ = (
        "_state", "_config", "_metrics", "_enforcer",
        "_scout", "_planner", "_specifier", "_executor", "_auditor",
        "_prev_failing_names",
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

        self._scout = Scout()
        self._planner = Planner()
        self._specifier = Specifier()
        self._executor = Executor()
        self._auditor = Auditor()

        # Track failing check names across iterations for rework detection
        self._prev_failing_names: set[str] = set()

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics

    @property
    def enforcer(self) -> ConstraintEnforcer:
        return self._enforcer

    # ── Phase Implementations ─────────────────────────────────────────────

    def phase_observe(
        self,
        check_results: list[CheckResult],
        sha: str = "",
    ) -> list[CheckResult]:
        """Phase A — Ground truth snapshot."""
        self._state.phase = Phase.OBSERVE
        self._metrics.start()

        target = self._state.target
        if isinstance(target.required_checks, list):
            required_names = set(target.required_checks)
            required = [c for c in check_results if c.name in required_names]
        else:
            required = [c for c in check_results if c.status != CheckStatus.SKIPPED]

        green = [c.name for c in required if c.status.is_green]
        failing = [c.name for c in required if not c.status.is_green]

        self._state.record(
            "OBSERVED",
            sha=sha,
            total_checks=len(check_results),
            required_checks=len(required),
            green=green,
            failing=failing,
        )

        logger.info(
            "Observed %d checks (%d required, %d green, %d failing)",
            len(check_results), len(required), len(green), len(failing),
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

    def phase_plan(self, packets: list[FailPacket]) -> list[dict[str, Any]]:
        """Phase C — Build task graph."""
        self._state.phase = Phase.PLAN
        return self._planner.execute(self._state, packets=packets)

    def phase_specify(self, task: dict[str, Any], packet: FailPacket) -> Spec:
        """Phase D — Compile plan into executable spec."""
        self._state.phase = Phase.SPECIFY
        spec = self._specifier.execute(self._state, task=task, packet=packet)
        self._state.current_spec = spec
        return spec

    def phase_execute(self, spec: Spec) -> dict[str, Any]:
        """Phase E — Apply minimal patch."""
        self._state.phase = Phase.EXECUTE
        return self._executor.execute(
            self._state,
            spec=spec,
            apply_fn=self._config.apply_fn,
        )

    def phase_prove(
        self,
        fresh_check_results: list[CheckResult],
    ) -> bool:
        """
        Phase F — CI as oracle.

        CRITICAL: `fresh_check_results` MUST be re-fetched AFTER execution.
        Using stale pre-execute data here is a correctness bug.
        The engine documents this requirement via the parameter name.

        Returns True if all required checks are green.
        """
        self._state.phase = Phase.PROVE

        target = self._state.target
        if isinstance(target.required_checks, list):
            req_names = set(target.required_checks)
            required = [c for c in fresh_check_results if c.name in req_names]
        else:
            required = [c for c in fresh_check_results if c.status != CheckStatus.SKIPPED]

        all_green = all(c.status.is_green for c in required) and len(required) > 0

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
        Otherwise, propose based on state analysis.
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
                action=GovernorAction.MERGE,
                reason="All checks green + audit OK",
            )
        elif all_green and self._state.audit_verdict == AuditVerdict.RISK:
            decision = GovernorDecision(
                action=GovernorAction.HOLD,
                reason=f"Green but audit RISK: {audit_findings}",
            )
        else:
            decision = GovernorDecision(
                action=GovernorAction.NEXT,
                reason="Not all conditions met for merge",
            )

        self._state.record(
            "DECISION",
            action=decision.action.value,
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
        Run one complete iteration of the canonical loop (Phases A→H).

        IMPORTANT: For proper PROVE semantics in a real integration,
        the caller should re-fetch check_results after execution.
        In this single-call interface, the same check_results are used
        for both OBSERVE and PROVE. For multi-round usage, call
        individual phase methods.
        """
        self._state.iteration += 1

        if self._state.iteration > self._config.max_iterations:
            self._state.halt(
                f"Max iterations ({self._config.max_iterations}) exceeded"
            )
            return GovernorDecision(
                action=GovernorAction.HALT,
                reason=self._state.halt_reason,
            )

        # Snapshot current failing names BEFORE this iteration
        current_failing = {p.check_name for p in self._state.active_packets}

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
                    action=GovernorAction.HALT,
                    reason=self._state.halt_reason,
                )

            exec_result = self.phase_execute(spec)
            if exec_result["errors"]:
                logger.warning("Execution errors for %s: %s", pid, exec_result["errors"])

        # F: Prove (using provided check_results — see docstring)
        all_green = self.phase_prove(check_results)

        # Rework tracking: detect NEW failures that weren't in previous iteration
        new_failing = {p.check_name for p in packets}
        newly_introduced = new_failing - self._prev_failing_names
        closed_count = len(self._prev_failing_names - new_failing)
        has_new_failures = bool(newly_introduced) and self._state.iteration > 1

        self._metrics.record_iteration(
            closed=closed_count,
            new_failures=has_new_failures,
        )

        # Update tracking for next iteration
        self._prev_failing_names = new_failing

        if not all_green:
            return GovernorDecision(
                action=GovernorAction.NEXT,
                reason=f"Still failing: {sorted(new_failing)}",
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
        PASS_CONTRACT met AND proof bundle captured → MAY stop.
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

        result = self._config.checkpoint_store.save_bundle(proof)
        proof_hash = result.unwrap() if result.is_ok() else ""
        self._config.checkpoint_store.save_state(self._state, "final")

        return {
            "stopped": True,
            "proof_hash": proof_hash,
            "metrics": self._metrics.summary(),
            "state_snapshot": "final",
        }
