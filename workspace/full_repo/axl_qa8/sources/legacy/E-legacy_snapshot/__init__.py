"""
DAO-LIFEBOOK — Deterministic AI Orchestration as a Personal Engineering OS.

Core claim: Reality is whatever CI/Checks say;
            progress is measured by closed loops, not effort.
"""

__version__ = "2026.1.0"

from .models import (
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
from .constraints import ConstraintEnforcer, Violation
from .engine import CanonicalLoop, EngineConfig, GovernorDecision
from .evidence import CheckpointStore, ProofAssembler
from .metrics import Ledger, LoopMetrics
from .roles import Auditor, Executor, Planner, Scout, Specifier
from .truth_plane import CIOracle, LocalGate, PRRef

__all__ = [
    # Models
    "ArtifactRef", "AuditVerdict", "CheckResult", "CheckStatus",
    "Constraints", "DiffBudget", "DiffSummary", "EditInstruction",
    "EvidencePointer", "FailPacket", "LocalGateResult", "LoopState",
    "Phase", "ProofBundle", "RefactorPolicy", "SecurityPolicy",
    "Spec", "TargetState", "TimeSpan",
    # Constraints
    "ConstraintEnforcer", "Violation",
    # Engine
    "CanonicalLoop", "EngineConfig", "GovernorDecision",
    # Evidence
    "CheckpointStore", "ProofAssembler",
    # Metrics
    "Ledger", "LoopMetrics",
    # Roles
    "Auditor", "Executor", "Planner", "Scout", "Specifier",
    # Truth Plane
    "CIOracle", "LocalGate", "PRRef",
]
