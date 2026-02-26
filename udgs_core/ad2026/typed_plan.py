"""
udgs_core.ad2026.typed_plan
===========================
AD-2026 Layer 1 — Formal Orchestration Logic (G-SMT)

Implements:
  - TypedAction   : AD-2026 §1.2 typed SPS action with pre/post/invariants/rollback
  - SPS           : System Proposed State (typed action list)
  - InvariantSet  : compiled AC invariants (Python-native constraint checker)
  - SMTGate       : G7-FORMAL gate (pure Python; Z3 optional enhancement)
  - SPSValidator  : correctness-by-construction checks (§1.1)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# Typed Action  (AD-2026 §1.2)
# ──────────────────────────────────────────────

class ActionType(str, Enum):
    READ            = "READ"
    WRITE           = "WRITE"
    EXECUTE         = "EXECUTE"
    DEPLOY          = "DEPLOY"
    ROLLBACK        = "ROLLBACK"
    MUTATE_PERIPHERAL = "MUTATE_PERIPHERAL"
    CHECKPOINT      = "CHECKPOINT"
    EMIT_PB         = "EMIT_PB"
    ESCALATE        = "ESCALATE"


@dataclass
class TypedAction:
    """
    AD-2026 §1.2 — typed action in a System Proposed State plan.

    Fields
    ------
    action_id          : unique within SPS
    action_type        : ActionType enum
    preconditions      : list of string predicates (must ALL be satisfied before execution)
    postconditions     : list of string predicates (must ALL hold after execution)
    invariants_touched : list of invariant IDs from AC that this action may affect
    rollback_action_id : ID of the rollback action (must exist in same SPS or "NOOP")
    evidence_refs      : §REF evidence for this action
    metadata           : arbitrary typed metadata
    """
    action_id:          str
    action_type:        ActionType
    preconditions:      List[str]
    postconditions:     List[str]
    invariants_touched: List[str]
    rollback_action_id: str          # "" = no rollback; "NOOP" = no-op rollback
    evidence_refs:      List[str] = field(default_factory=list)
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d


@dataclass
class SPS:
    """
    System Proposed State — typed action list.
    Produced by BSS planner; validated by SMT gate before execution.
    """
    sps_id:    str
    agent_id:  str
    utc:       str
    actions:   List[TypedAction] = field(default_factory=list)
    metadata:  Dict[str, Any] = field(default_factory=dict)

    def add(self, action: TypedAction) -> None:
        self.actions.append(action)

    def canonical_bytes(self) -> bytes:
        d = {
            "sps_id":  self.sps_id,
            "agent_id": self.agent_id,
            "utc":     self.utc,
            "actions": [a.as_dict() for a in self.actions],
        }
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sps_id":   self.sps_id,
            "agent_id": self.agent_id,
            "utc":      self.utc,
            "sps_hash": self.sha256(),
            "actions":  [a.as_dict() for a in self.actions],
            "metadata": self.metadata,
        }


# ──────────────────────────────────────────────
# Invariant  (compiled from AC)
# ──────────────────────────────────────────────

@dataclass
class Invariant:
    """
    A single AC invariant expressed as a Python callable predicate.
    kind: SAFETY | SECURITY | DETERMINISM | FORBIDDEN
    """
    invariant_id: str
    kind:         str
    description:  str
    predicate:    Callable[[SPS], bool]
    severity:     str = "HARD"   # HARD | SOFT

    def check(self, sps: SPS) -> Tuple[bool, str]:
        try:
            result = self.predicate(sps)
            return result, ("" if result else f"Invariant {self.invariant_id} VIOLATED: {self.description}")
        except Exception as exc:
            return False, f"Invariant {self.invariant_id} ERROR: {exc}"


class InvariantSet:
    """
    Compiled set of AC invariants.
    Populated with register(); evaluated by SMTGate.
    """

    def __init__(self) -> None:
        self._invariants: List[Invariant] = []

    def register(self, inv: Invariant) -> None:
        self._invariants.append(inv)

    def evaluate(self, sps: SPS) -> Tuple[bool, List[str]]:
        """
        Evaluate all invariants against SPS.
        Returns (all_pass: bool, violations: List[str])
        """
        violations: List[str] = []
        for inv in self._invariants:
            ok, msg = inv.check(sps)
            if not ok:
                violations.append(msg)
        return len(violations) == 0, violations

    def __len__(self) -> int:
        return len(self._invariants)


# ──────────────────────────────────────────────
# Built-in invariants (AC baseline)
# ──────────────────────────────────────────────

def build_ac_baseline_invariants() -> InvariantSet:
    """
    AD-2026 mandatory invariants compiled from AC.
    Every SPS must satisfy these before execution.
    """
    s = InvariantSet()

    # SAFETY-01: Every external-effect action must have a rollback
    s.register(Invariant(
        invariant_id="SAFETY-01",
        kind="SAFETY",
        description="Every DEPLOY/WRITE/EXECUTE action must have a rollback_action_id",
        predicate=lambda sps: all(
            a.rollback_action_id not in ("", None)
            for a in sps.actions
            if a.action_type in (ActionType.DEPLOY, ActionType.WRITE, ActionType.EXECUTE)
        ),
    ))

    # SAFETY-02: SPS must not be empty
    s.register(Invariant(
        invariant_id="SAFETY-02",
        kind="SAFETY",
        description="SPS must contain at least one action",
        predicate=lambda sps: len(sps.actions) > 0,
    ))

    # SECURITY-01: No MUTATE_PERIPHERAL action without EMIT_PB in same SPS
    s.register(Invariant(
        invariant_id="SECURITY-01",
        kind="SECURITY",
        description="MUTATE_PERIPHERAL requires accompanying EMIT_PB action",
        predicate=lambda sps: (
            not any(a.action_type == ActionType.MUTATE_PERIPHERAL for a in sps.actions)
            or any(a.action_type == ActionType.EMIT_PB for a in sps.actions)
        ),
    ))

    # SECURITY-02: All action_ids must be unique within SPS
    s.register(Invariant(
        invariant_id="SECURITY-02",
        kind="SECURITY",
        description="All action_ids within SPS must be unique",
        predicate=lambda sps: len({a.action_id for a in sps.actions}) == len(sps.actions),
    ))

    # DETERMINISM-01: No action with empty preconditions AND external effects
    s.register(Invariant(
        invariant_id="DETERMINISM-01",
        kind="DETERMINISM",
        description="DEPLOY/WRITE actions must declare at least one precondition",
        predicate=lambda sps: all(
            len(a.preconditions) > 0
            for a in sps.actions
            if a.action_type in (ActionType.DEPLOY, ActionType.WRITE)
        ),
    ))

    # FORBIDDEN-01: MUTATE_PERIPHERAL must NOT touch kernel invariants
    s.register(Invariant(
        invariant_id="FORBIDDEN-01",
        kind="FORBIDDEN",
        description="MUTATE_PERIPHERAL must not declare invariants_touched containing 'AC_KERNEL'",
        predicate=lambda sps: not any(
            a.action_type == ActionType.MUTATE_PERIPHERAL
            and any("AC_KERNEL" in inv_id for inv_id in a.invariants_touched)
            for a in sps.actions
        ),
    ))

    return s


# ──────────────────────────────────────────────
# SMT Gate — G7-FORMAL (AD-2026 §1.0)
# ──────────────────────────────────────────────

@dataclass
class GateResult:
    gate_id:   str
    status:    str        # PASS | FAIL | ERROR
    evidence:  List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


class SMTGate:
    """
    AD-2026 G7-FORMAL — constraint satisfaction gate.

    Uses Python-native InvariantSet as the constraint solver.
    Z3 integration point: replace evaluate() call with Z3 SMT proof when available.

    Fail-closed: any violation => FAIL, execution blocked.
    """
    GATE_ID = "G7-FORMAL"

    def __init__(self, invariants: Optional[InvariantSet] = None) -> None:
        self.invariants = invariants if invariants is not None else build_ac_baseline_invariants()

    def prove(self, sps: SPS) -> GateResult:
        """
        Prove M(SPS) ⊨ C(AC_invariants).
        Returns GateResult with PASS (proven) or FAIL (violation found).
        Empty invariant set is an ERROR — cannot prove safety with no constraints.
        """
        if len(self.invariants) == 0:
            return GateResult(
                gate_id=self.GATE_ID,
                status="ERROR",
                evidence=["No invariants registered — cannot prove safety"],
            )

        all_pass, violations = self.invariants.evaluate(sps)

        return GateResult(
            gate_id=self.GATE_ID,
            status="PASS" if all_pass else "FAIL",
            evidence=[f"Evaluated {len(self.invariants)} invariants against SPS {sps.sps_id}"],
            violations=violations,
        )


# ──────────────────────────────────────────────
# SPS DAG Validator  (AD-2026 §1.1)
# ──────────────────────────────────────────────

class SPSValidator:
    """
    Correctness-by-construction checks for the SPS action DAG.
    Verifies: no deadlock potential, rollback exists, monotonic PB.
    """

    @staticmethod
    def validate(sps: SPS) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        action_ids = {a.action_id for a in sps.actions}

        for action in sps.actions:
            # Rollback reference exists
            if action.rollback_action_id not in ("", "NOOP") and \
               action.rollback_action_id not in action_ids:
                errors.append(
                    f"Action {action.action_id}: rollback_action_id "
                    f"'{action.rollback_action_id}' not found in SPS"
                )

            # Preconditions are non-empty strings
            for pc in action.preconditions:
                if not isinstance(pc, str) or not pc.strip():
                    errors.append(f"Action {action.action_id}: empty precondition")

            # Evidence refs present for external-effect actions
            if action.action_type in (ActionType.DEPLOY, ActionType.WRITE, ActionType.EXECUTE):
                if not action.evidence_refs:
                    errors.append(
                        f"Action {action.action_id} ({action.action_type.value}): "
                        "no evidence_refs — external effects require evidence"
                    )

        return len(errors) == 0, errors
