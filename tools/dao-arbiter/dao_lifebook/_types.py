"""
DAO-LIFEBOOK — Core Type System.

Provides:
  • Result[T, E]  — typed success/failure monad (no exceptions for control flow)
  • Error hierarchy — structured, machine-readable errors
  • Type aliases  — canonical types used across all modules

Design: if a function can fail in expected ways, it returns Result.
Exceptions are reserved for programming errors (bugs), not business logic.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Generic, TypeVar, TypeAlias, Any, final

T = TypeVar("T")
E = TypeVar("E")


# ─── Result Monad ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success branch of Result."""
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_err(self) -> Any:
        raise TypeError(f"Called unwrap_err on Ok({self.value!r})")

    def map(self, fn):  # type: ignore[no-untyped-def]
        return Ok(fn(self.value))

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failure branch of Result."""
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        raise TypeError(f"Called unwrap on Err({self.error!r})")

    def unwrap_err(self) -> E:
        return self.error

    def map(self, fn):  # type: ignore[no-untyped-def]
        return self

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


Result: TypeAlias = Ok[T] | Err[E]


# ─── Error Hierarchy ──────────────────────────────────────────────────────────

class ErrorSeverity(str, enum.Enum):
    HALT     = "halt"       # System stops, human must intervene
    RETRY    = "retry"      # Transient, may recover
    DEGRADED = "degraded"   # Continue with reduced capability
    INFO     = "info"       # Logged but not actionable


@dataclass(frozen=True, slots=True)
class DAOError:
    """Structured error — machine-readable, never just a string."""
    code: str
    message: str
    severity: ErrorSeverity = ErrorSeverity.HALT
    context: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@final
class EC:
    """Error codes — canonical, grep-able constants."""
    # Constraint violations
    PATH_DENIED             = "CONSTRAINT_PATH_DENIED"
    PATH_NOT_ALLOWED        = "CONSTRAINT_PATH_NOT_ALLOWED"
    DIFF_BUDGET             = "CONSTRAINT_DIFF_BUDGET"
    REFACTOR_BLOCKED        = "CONSTRAINT_REFACTOR"
    SECURITY_VIOLATION      = "CONSTRAINT_SECURITY"

    # Engine
    MAX_ITER_EXCEEDED       = "MAX_ITERATIONS_EXCEEDED"
    GOVERNOR_HALT           = "GOVERNOR_HALT"
    PHASE_INVARIANT         = "PHASE_INVARIANT_VIOLATED"
    STALE_DATA              = "STALE_DATA"

    # Truth Plane
    API_TIMEOUT             = "API_TIMEOUT"
    API_AUTH_FAILED         = "API_AUTH_FAILED"
    API_RATE_LIMITED        = "API_RATE_LIMITED"
    API_NOT_FOUND           = "API_NOT_FOUND"
    API_SERVER_ERROR        = "API_SERVER_ERROR"
    PR_PARSE_FAILED         = "PR_PARSE_FAILED"

    # Execution
    GATE_TIMEOUT            = "GATE_TIMEOUT"
    GATE_FAILED             = "GATE_FAILED"
    APPLY_FAILED            = "APPLY_FN_FAILED"

    # Evidence
    CHECKPOINT_IO           = "CHECKPOINT_IO_ERROR"
    INTEGRITY_MISMATCH      = "INTEGRITY_MISMATCH"
    SCHEMA_MISMATCH         = "SCHEMA_VERSION_MISMATCH"
    BUNDLE_INCOMPLETE       = "BUNDLE_INCOMPLETE"


# ─── Aliases ──────────────────────────────────────────────────────────────────

SHA256Hex: TypeAlias = str
GitSHA: TypeAlias = str
Seconds: TypeAlias = float
