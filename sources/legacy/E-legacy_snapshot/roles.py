"""
DAO-LIFEBOOK — Role Graph (§3).

Each role has a narrow contract. Agents do not overlap by default.
Overlap must be deliberate.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

from .models import (
    AuditVerdict,
    CheckResult,
    CheckStatus,
    Constraints,
    DiffSummary,
    FailPacket,
    LoopState,
    ProofBundle,
    Spec,
    TargetState,
    EditInstruction,
    CommandExpectation,
    Acceptance,
)
from .constraints import ConstraintEnforcer, Violation

logger = logging.getLogger("dao.roles")


# ─── Abstract Role Contract ──────────────────────────────────────────────────

class Role(abc.ABC):
    """Base contract every role satisfies."""

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def execute(self, state: LoopState, **ctx: Any) -> Any:
        """
        Perform the role's function.
        Roles ONLY propose; they never decide "done".
        """
        ...


# ─── R1 SCOUT — Signal Harvester ─────────────────────────────────────────────

class Scout(Role):
    """
    Opens PR checks / runs / logs.
    Outputs FAIL-PACKETs, ranked by blocking severity.
    """

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
        """Extract failing required checks → ordered FailPackets."""
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

        packets.sort(key=lambda p: p.severity)
        state.record("SCOUT_HARVESTED", count=len(packets))
        logger.info("Scout harvested %d fail packets", len(packets))
        return packets


# ─── R2 PLANNER — Task Graph Builder ─────────────────────────────────────────

class Planner(Role):
    """
    Converts FAIL_PACKETs into ordered tasks + risk notes.
    Outputs PLAN with bounded scope and success criteria.
    """

    @property
    def name(self) -> str:
        return "R2_PLANNER"

    def execute(
        self,
        state: LoopState,
        *,
        packets: list[FailPacket],
    ) -> list[dict[str, Any]]:
        """
        Build a minimal task graph from packets.
        Returns ordered list of task dicts.
        """
        plan: list[dict[str, Any]] = []

        for packet in packets:
            task = {
                "packet_id": packet.id,
                "check_name": packet.check_name,
                "objective": packet.done_when,
                "risk": self._assess_risk(packet, state.constraints),
                "priority": packet.severity,
                "rollback": f"git revert to pre-{packet.id} state",
            }
            plan.append(task)

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
            risks.append("no local repro command available")
        return "; ".join(risks) if risks else "low"


# ─── R3 SPECIFIER — Protocol Compiler ────────────────────────────────────────

class Specifier(Role):
    """
    Writes an executable protocol for the executor.
    Outputs SPEC: precise edits + commands + acceptance tests.
    """

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
        """Compile one task into an executable Spec."""
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
    Outputs PATCH + local gate results.

    NOTE: This role provides the *framework* for execution.
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
        """
        Execute a spec. If apply_fn is provided, call it with the spec.
        Otherwise, run spec commands via LocalGate.

        Returns execution result dict.
        """
        from .truth_plane import LocalGate

        result: dict[str, Any] = {
            "spec_objective": spec.objective,
            "edits_applied": False,
            "gate_results": [],
            "errors": [],
        }

        # Apply edits via callback (agent integration point)
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
            exit_code, output = LocalGate.run(cmd_spec.cmd)
            passed = self._check_expectation(exit_code, output, cmd_spec.expect)
            result["gate_results"].append({
                "cmd": cmd_spec.cmd,
                "exit_code": exit_code,
                "passed": passed,
                "output_tail": output[-500:] if len(output) > 500 else output,
            })
            if not passed:
                result["errors"].append(
                    f"Gate failed: {cmd_spec.cmd} (exit={exit_code})"
                )

        state.record(
            "EXECUTED",
            edits=result["edits_applied"],
            gates=len(result["gate_results"]),
            errors=len(result["errors"]),
        )
        return result

    @staticmethod
    def _check_expectation(exit_code: int, output: str, expect: str) -> bool:
        if expect == "exit 0":
            return exit_code == 0
        if expect.startswith("exit "):
            try:
                return exit_code == int(expect.split()[1])
            except (IndexError, ValueError):
                return False
        if expect.startswith("output contains "):
            needle = expect[len("output contains "):]
            return needle in output
        return exit_code == 0


# ─── R5 AUDITOR — Post-Green Correctness Gate ────────────────────────────────

class Auditor(Role):
    """
    Validates minimality, scope, security posture, semantic correctness.
    Outputs AUDIT_VERDICT: OK | RISK | NEEDS_CHANGE with evidence pointers.
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
        """
        Post-green audit.

        Returns (verdict, list_of_findings).
        """
        findings: list[str] = []

        # G1a: All required checks green?
        non_green = [c for c in check_results if not c.status.is_green]
        if non_green:
            findings.append(
                f"Non-green checks remain: "
                f"{[c.name for c in non_green]}"
            )

        # G1b: Green by omission? (skipped checks)
        skipped = [c for c in check_results if c.status == CheckStatus.SKIPPED]
        if skipped:
            findings.append(
                f"Skipped checks (potential green-by-omission): "
                f"{[c.name for c in skipped]}"
            )

        # G1c: Constraint enforcement
        if enforcer:
            violations = enforcer.enforce_all(
                touched_paths=touched_files,
                diff=diff_summary,
            )
            for v in violations:
                findings.append(f"CONSTRAINT VIOLATION [{v.rule}]: {v.detail}")

        # G1d: Diff budget check
        budget = state.constraints.diff_budget
        if diff_summary.files_changed > budget.max_files:
            findings.append(
                f"Diff budget exceeded: {diff_summary.files_changed} files "
                f"> {budget.max_files} max"
            )
        if abs(diff_summary.loc_delta) > budget.max_loc:
            findings.append(
                f"LOC budget exceeded: {diff_summary.loc_delta} "
                f"> ±{budget.max_loc} max"
            )

        # Determine verdict
        has_violations = any("CONSTRAINT VIOLATION" in f for f in findings)
        has_non_green = bool(non_green)

        if has_violations or has_non_green:
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
        logger.info("Auditor verdict: %s (%d findings)", verdict.value, len(findings))
        return verdict, findings
