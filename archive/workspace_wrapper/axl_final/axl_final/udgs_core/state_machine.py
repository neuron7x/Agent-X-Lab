from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class LoopState(str, Enum):
    FAIL = "FAIL"
    FIX = "FIX"
    PROVE = "PROVE"
    CHECKPOINT = "CHECKPOINT"
    HALT = "HALT"


@dataclass(frozen=True)
class Invariant:
    name: str
    rule: str  # human-readable contract
    severity: str = "ERROR"  # ERROR|WARN


@dataclass
class Evidence:
    logs: Dict[str, Any] | None = None
    hash_anchor: str | None = None
    oracle_pass: bool | None = None  # Optional: CI says PASS/FAIL (True/False)


@dataclass
class CycleResult:
    next_state: LoopState
    violated: List[Invariant] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class DeterministicCycle:
    """
    Canonical loop: FAIL → FIX → PROVE → CHECKPOINT
    Fail-closed: any missing evidence at PROVE → HALT.
    """

    def __init__(self, *, fail_closed: bool = True) -> None:
        self.state: LoopState = LoopState.FAIL
        self.fail_closed = fail_closed
        self.history: List[Tuple[LoopState, Dict[str, Any]]] = []

    def step(self, evidence: Evidence) -> CycleResult:
        violated: List[Invariant] = []
        notes: List[str] = []

        if self.state == LoopState.FAIL:
            self.state = LoopState.FIX
            notes.append("Transition FAIL→FIX")
        elif self.state == LoopState.FIX:
            self.state = LoopState.PROVE
            notes.append("Transition FIX→PROVE")
        elif self.state == LoopState.PROVE:
            # Fail-closed gate: require logs + hash_anchor (and optionally oracle_pass=True if provided)
            if evidence.logs is None:
                violated.append(Invariant("EVIDENCE_LOGS_REQUIRED", "PROVE requires evidence.logs"))
            if not evidence.hash_anchor:
                violated.append(Invariant("HASH_ANCHOR_REQUIRED", "PROVE requires evidence.hash_anchor"))

            if evidence.oracle_pass is False:
                violated.append(Invariant("ORACLE_FAILED", "External oracle reports FAIL"))

            if violated and self.fail_closed:
                self.state = LoopState.HALT
                notes.append("Fail-closed gate: HALT due to violated invariants")
            else:
                self.state = LoopState.CHECKPOINT
                notes.append("PROVE gate satisfied: PROVE→CHECKPOINT")

        elif self.state == LoopState.CHECKPOINT:
            self.state = LoopState.FAIL
            notes.append("CHECKPOINT→FAIL (new loop)")
        elif self.state == LoopState.HALT:
            notes.append("HALT: no transitions")

        self.history.append((self.state, {
            "logs_present": evidence.logs is not None,
            "hash_anchor_present": bool(evidence.hash_anchor),
            "oracle_pass": evidence.oracle_pass,
        }))
        return CycleResult(self.state, violated, notes)
