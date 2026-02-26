"""
DAO-LIFEBOOK — Deterministic AI Orchestration as a Personal Engineering OS.

Core claim: Reality is whatever CI/Checks say;
            progress is measured by closed loops, not effort.
"""

__version__ = "2026.2.0"

from .models import (
    SCHEMA_VERSION,
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
    GovernorAction,
    GovernorDecision,
    HistoryEvent,
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
from ._types import (
    Result,
    Ok,
    Err,
    DAOError,
    ErrorSeverity,
    EC,
)
from .constraints import ConstraintEnforcer, Violation
from .engine import CanonicalLoop, EngineConfig
from .evidence import CheckpointStore, ProofAssembler
from .metrics import Ledger, LoopMetrics
from .roles import Auditor, Executor, Planner, Scout, Specifier
from .truth_plane import CIOracle, LocalGate, PRRef

__all__ = [
    # Version
    "__version__", "SCHEMA_VERSION",
    # Result monad
    "Result", "Ok", "Err", "DAOError", "ErrorSeverity", "EC",
    # Models
    "ArtifactRef", "AuditVerdict", "CheckResult", "CheckStatus",
    "Constraints", "DiffBudget", "DiffSummary", "EditInstruction",
    "EvidencePointer", "FailPacket", "GovernorAction", "GovernorDecision",
    "HistoryEvent", "LocalGateResult", "LoopState", "Phase", "ProofBundle",
    "RefactorPolicy", "SecurityPolicy", "Spec", "TargetState", "TimeSpan",
    # Constraints
    "ConstraintEnforcer", "Violation",
    # Engine
    "CanonicalLoop", "EngineConfig",
    # Evidence
    "CheckpointStore", "ProofAssembler",
    # Metrics
    "Ledger", "LoopMetrics",
    # Roles
    "Auditor", "Executor", "Planner", "Scout", "Specifier",
    # Truth Plane
    "CIOracle", "LocalGate", "PRRef",
]
