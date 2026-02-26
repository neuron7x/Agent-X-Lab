"""
DAO-LIFEBOOK — Role Graph (§3).

Each role has a narrow contract. Agents do not overlap by default.
Roles ONLY propose; they never decide "done".

v2 improvements:
  • Protocol-based Role contract (structural typing)
  • Executor returns structured LocalGateResult
  • Auditor uses ConstraintEnforcer (no duplication)
  • Better risk assessment in Planner
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Protocol, runtime_checkable

from .models import (
    Acceptance,
    AuditVerdict,
    CheckResult,
    CheckStatus,
    CommandExpectation,
    Constraints,
    DiffSummary,
    EditInstruction,
    FailPacket,
    LocalGateResult,
    LoopState,
    Spec,
)
from .constraints import ConstraintEnforcer, Violation

logger = logging.getLogger("dao.roles")


# ─── Role Contract (Protocol for structural typing) ──────────────────────────

@runtime_checkable
class RoleProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def execute(self, state: LoopState, **ctx: Any) -> Any: ...


class Role(abc.ABC):
    """Base contract — abstract base for all roles."""

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def execute(self, state: LoopState, **ctx: Any) -> Any: ...


# ─── R1 SCOUT — Signal Harvester ─────────────────────────────────────────────

class Scout(Role):
    """Opens PR checks, outputs ranked FAIL-PACKETs."""

    @property
    def name(self) -> str:
        return "R1_SCOUT"

    def execute(
        self,
        state: LoopState,
        *,
        all_checks: list[CheckResult],
        required_names: list[str] | None = None,
    ) -> list[FailPacket]:
        # Filter to required
        if required_names:
            req_set = set(required_names)
            required = [c for c in all_checks if c.name in req_set]
        else:
            required = [c for c in all_checks if c.status != CheckStatus.SKIPPED]

        failing = [c for c in required if not c.status.is_green]

        packets: list[FailPacket] = []
        for idx, check in enumerate(failing):
            severity = 0 if check.status == CheckStatus.FAILURE else 1
            packets.append(FailPacket(
                id=f"FP-{state.iteration:03d}-{idx:03d}",
                check_name=check.name,
                error_extract=[
                    f"[{check.status.value}] {check.name}",
                    f"Run: {check.run_url}" if check.run_url else "No run URL",
                ],
                done_when=f"'{check.name}' status == success",
                severity=severity,
            ))

        packets.sort(key=lambda p: (p.severity, p.check_name))
        state.record("SCOUT_HARVESTED", count=len(packets))
        logger.info("Scout harvested %d fail packets", len(packets))
        return packets


# ─── R2 PLANNER — Task Graph Builder ─────────────────────────────────────────

class Planner(Role):
    """Converts FAIL_PACKETs into ordered tasks with risk assessment."""

    @property
    def name(self) -> str:
        return "R2_PLANNER"

    def execute(
        self,
        state: LoopState,
        *,
        packets: list[FailPacket],
    ) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []
        already_closed = set(state.closed_packet_ids)

        for packet in packets:
            if packet.id in already_closed:
                continue

            task = {
                "packet_id": packet.id,
                "check_name": packet.check_name,
                "objective": packet.done_when,
                "risk": self._assess_risk(packet, state.constraints),
                "priority": packet.severity,
                "rollback": f"git revert to pre-{packet.id} state",
            }
            plan.append(task)

        # Sort by priority (0 = most urgent)
        plan.sort(key=lambda t: t["priority"])

        state.record("PLAN_BUILT", tasks=len(plan))
        logger.info("Planner built %d tasks", len(plan))
        return plan

    @staticmethod
    def _assess_risk(packet: FailPacket, constraints: Constraints) -> str:
        risks: list[str] = []

        if packet.file_line:
            path = packet.file_line.split(":")[0]
            for deny in constraints.touch_denylist:
                if path.startswith(deny.rstrip("*").rstrip("/")):
                    risks.append(f"touches deny-listed path: {deny}")

        if not packet.repro_cmd:
            risks.append("no local repro command")

        # Check if this is a recurring failure (iteration > 1)
        if packet.id and "-" in packet.id:
            parts = packet.id.split("-")
            if len(parts) >= 2:
                try:
                    iter_num = int(parts[1])
                    if iter_num > 1:
                        risks.append(f"recurring since iteration {iter_num}")
                except ValueError:
                    pass

        return "; ".join(risks) if risks else "low"


# ─── R3 SPECIFIER — Protocol Compiler ────────────────────────────────────────

class Specifier(Role):
    """Writes executable protocol for the executor."""

    @property
    def name(self) -> str:
        return "R3_SPECIFIER"

    def execute(
        self,
        state: LoopState,
        *,
        task: dict[str, Any],
        packet: FailPacket,
    ) -> Spec:
        scope_files: list[str] = []
        if packet.file_line:
            scope_files.append(packet.file_line.split(":")[0])

        edits: list[EditInstruction] = []
        if scope_files:
            edits.append(EditInstruction(
                file=scope_files[0],
                change=f"Fix: {packet.done_when}",
            ))

        commands: list[CommandExpectation] = []
        if packet.repro_cmd:
            commands.append(CommandExpectation(
                cmd=packet.repro_cmd,
                expect="exit 0",
            ))

        spec = Spec(
            objective=f"Close {packet.id}: {packet.done_when}",
            scope_files=scope_files,
            scope_deny=list(state.constraints.touch_denylist),
            edits=edits,
            commands=commands,
            acceptance=Acceptance(
                must_pass=[packet.check_name],
                must_not=["new failures introduced"],
            ),
            rollback_plan=task.get("rollback", "git stash pop"),
        )

        state.record("SPEC_COMPILED", packet_id=packet.id)
        logger.info("Specifier compiled spec for %s", packet.id)
        return spec


# ─── R4 EXECUTOR — Patch Generator ───────────────────────────────────────────

class Executor(Role):
    """
    Implements minimal diffs under constraints.
    Actual file edits are delegated to agent callbacks.
    """

    @property
    def name(self) -> str:
        return "R4_EXECUTOR"

    def execute(
        self,
        state: LoopState,
        *,
        spec: Spec,
        apply_fn: Any | None = None,
    ) -> dict[str, Any]:
        from .truth_plane import LocalGate

        result: dict[str, Any] = {
            "spec_objective": spec.objective,
            "edits_applied": False,
            "gate_results": [],
            "errors": [],
        }

        # Apply edits via callback
        if apply_fn is not None:
            try:
                apply_fn(spec)
                result["edits_applied"] = True
            except Exception as exc:
                result["errors"].append(f"apply_fn failed: {exc}")
                state.record("EXECUTE_FAIL", error=str(exc))
                return result

        # Run local gates
        for cmd_spec in spec.commands:
            gate_result = LocalGate.run(
                cmd_spec.cmd,
                timeout=cmd_spec.timeout_seconds,
            )
            result["gate_results"].append(gate_result.model_dump())

            if not gate_result.passed:
                result["errors"].append(
                    f"Gate failed: {cmd_spec.cmd} (exit={gate_result.exit_code})"
                )

        state.record(
            "EXECUTED",
            edits=result["edits_applied"],
            gates=len(result["gate_results"]),
            errors=len(result["errors"]),
        )
        return result


# ─── R5 AUDITOR — Post-Green Correctness Gate ────────────────────────────────

class Auditor(Role):
    """
    Validates minimality, scope, security posture, semantic correctness.
    Outputs AUDIT_VERDICT: OK | RISK | NEEDS_CHANGE with evidence.
    """

    @property
    def name(self) -> str:
        return "R5_AUDITOR"

    def execute(
        self,
        state: LoopState,
        *,
        check_results: list[CheckResult],
        diff_summary: DiffSummary,
        touched_files: list[str],
        enforcer: ConstraintEnforcer | None = None,
    ) -> tuple[AuditVerdict, list[str]]:
        findings: list[str] = []

        # A1: Required checks that are actively failing (not just skipped)?
        actually_failing = [
            c for c in check_results
            if c.status in (CheckStatus.FAILURE, CheckStatus.PENDING, CheckStatus.UNKNOWN)
        ]
        if actually_failing:
            findings.append(
                f"Failing checks: {[c.name for c in actually_failing]}"
            )

        # A2: Green by omission? (skipped checks that were expected)
        skipped = [c for c in check_results if c.status == CheckStatus.SKIPPED]
        if skipped:
            findings.append(
                f"Skipped checks (green-by-omission risk): {[c.name for c in skipped]}"
            )

        # A3: Constraint enforcement (single source of truth)
        if enforcer:
            violations = enforcer.enforce_all(
                touched_paths=touched_files,
                diff=diff_summary,
            )
            for v in violations:
                findings.append(f"CONSTRAINT [{v.rule}]: {v.detail}")

        # Determine verdict
        has_violations = any("CONSTRAINT" in f for f in findings)
        has_failing = bool(actually_failing)

        if has_violations or has_failing:
            verdict = AuditVerdict.NEEDS_CHANGE
        elif findings:
            verdict = AuditVerdict.RISK
        else:
            verdict = AuditVerdict.OK

        state.record(
            "AUDIT_COMPLETE",
            verdict=verdict.value,
            findings_count=len(findings),
        )
        logger.info("Auditor: %s (%d findings)", verdict.value, len(findings))
        return verdict, findings
