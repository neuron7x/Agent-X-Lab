"""
DAO-LIFEBOOK — Data Model Layer.

Strict I/O schemas (§4). Every structure is validated at construction.
Ambiguity resolves FAIL-CLOSED (A1 normative language).
Model text is never truth; it is a proposal (Axiom A1).
"""

from __future__ import annotations

import hashlib
import enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)


# ─── Enumerations ────────────────────────────────────────────────────────────

class CheckStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"

    @property
    def is_terminal(self) -> bool:
        return self in (CheckStatus.SUCCESS, CheckStatus.FAILURE, CheckStatus.SKIPPED)

    @property
    def is_green(self) -> bool:
        return self == CheckStatus.SUCCESS


class Phase(str, enum.Enum):
    """Canonical loop phases (§5)."""
    OBSERVE    = "observe"
    PACKETIZE  = "packetize"
    PLAN       = "plan"
    SPECIFY    = "specify"
    EXECUTE    = "execute"
    PROVE      = "prove"
    AUDIT      = "audit"
    DECIDE     = "decide"
    HALTED     = "halted"
    MERGED     = "merged"


class AuditVerdict(str, enum.Enum):
    OK           = "ok"
    RISK         = "risk"
    NEEDS_CHANGE = "needs_change"


class RefactorPolicy(str, enum.Enum):
    NO_REFACTOR = "no-refactor"
    LIMITED     = "limited"
    ALLOWED     = "allowed"


class MaturityLevel(int, enum.Enum):
    """§9 maturity levels."""
    M0_MANUAL           = 0
    M1_STRUCTURED       = 1
    M2_MULTI_AGENT      = 2
    M3_AUTO_HARVEST     = 3
    M4_PARALLEL         = 4
    M5_PRODUCTIZED      = 5


# ─── Evidence Primitives ─────────────────────────────────────────────────────

class ArtifactRef(BaseModel):
    """Pointer to a build artifact with integrity hash."""
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str = ""

    @field_validator("sha256")
    @classmethod
    def _validate_hash(cls, v: str) -> str:
        if v and not (len(v) == 64 and all(c in "0123456789abcdef" for c in v)):
            raise ValueError(f"Invalid SHA-256 hex: {v!r}")
        return v

    @classmethod
    def from_file(cls, path: Path) -> ArtifactRef:
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls(path=str(path), sha256=h)


class EvidencePointer(BaseModel):
    """Traceability anchor into CI run logs (§4.3)."""
    model_config = ConfigDict(frozen=True)

    pr: str = ""
    run: str = ""
    log_anchor: str = ""


class CheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: CheckStatus
    run_url: str = ""


# ─── §4.1 TARGET_STATE ───────────────────────────────────────────────────────

class TargetState(BaseModel):
    """What must be true when the work is done."""
    model_config = ConfigDict(frozen=True)

    goal: str = Field(..., min_length=1)
    commands: list[str] = Field(default_factory=list)
    artifacts_expected: list[ArtifactRef] = Field(default_factory=list)
    required_checks: list[str] | Literal["auto-detect from PR"] = Field(
        default="auto-detect from PR"
    )
    done_when: list[str] = Field(..., min_length=1)

    @field_validator("done_when")
    @classmethod
    def _must_be_verifiable(cls, v: list[str]) -> list[str]:
        for stmt in v:
            if len(stmt.strip()) < 5:
                raise ValueError(
                    f"done_when statement too vague (< 5 chars): {stmt!r}"
                )
        return v


# ─── §4.2 CONSTRAINTS ────────────────────────────────────────────────────────

class SecurityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    no_disable_security_checks: bool = True
    actions_must_be_pinned: bool = True
    dependencies_must_be_pinned: bool = True


class DiffBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_files: int = Field(default=20, ge=1)
    max_loc: int = Field(default=500, ge=1)


class Constraints(BaseModel):
    """Safety rails — violation triggers HALT (Axiom A4)."""
    model_config = ConfigDict(frozen=True)

    touch_allowlist: list[str] = Field(default_factory=lambda: ["*"])
    touch_denylist: list[str] = Field(default_factory=list)
    diff_budget: DiffBudget = Field(default_factory=DiffBudget)
    refactor_policy: RefactorPolicy = RefactorPolicy.NO_REFACTOR
    security_policy: SecurityPolicy = Field(default_factory=SecurityPolicy)


# ─── §4.3 FAIL_PACKET ────────────────────────────────────────────────────────

class FailPacket(BaseModel):
    """Single source of iteration input — one failing check reduced to signal."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default="", description="Auto-assigned by packetizer")
    check_name: str = Field(..., min_length=1)
    error_extract: list[str] = Field(..., min_length=1, max_length=40)
    file_line: str | None = None
    repro_cmd: str | None = None
    done_when: str = Field(..., min_length=1)
    evidence_ptr: EvidencePointer = Field(default_factory=EvidencePointer)
    severity: int = Field(default=0, ge=0, description="0 = highest / merge-blocking")

    @field_validator("error_extract")
    @classmethod
    def _min_signal(cls, v: list[str]) -> list[str]:
        total = sum(len(line) for line in v)
        if total < 10:
            raise ValueError("error_extract has insufficient signal (< 10 chars total)")
        return v


# ─── §4.4 SPEC ───────────────────────────────────────────────────────────────

class EditInstruction(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: str
    change: str


class CommandExpectation(BaseModel):
    model_config = ConfigDict(frozen=True)

    cmd: str
    expect: str = "exit 0"


class Acceptance(BaseModel):
    model_config = ConfigDict(frozen=True)

    must_pass: list[str] = Field(default_factory=list)
    must_not: list[str] = Field(default_factory=list, description="No new failures")


class Spec(BaseModel):
    """Executable protocol — compiled from PLAN (§4.4)."""
    model_config = ConfigDict(frozen=True)

    objective: str
    scope_files: list[str] = Field(default_factory=list)
    scope_deny: list[str] = Field(default_factory=list)
    edits: list[EditInstruction] = Field(default_factory=list)
    commands: list[CommandExpectation] = Field(default_factory=list)
    acceptance: Acceptance = Field(default_factory=Acceptance)
    rollback_plan: str = ""


# ─── §4.5 PROOF_BUNDLE ───────────────────────────────────────────────────────

class LocalGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    cmd: str
    exit_code: int
    log_path: str = ""


class DiffSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    files_changed: int = Field(ge=0)
    loc_delta: int = 0


class TimeSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    t_start: datetime
    t_green: datetime | None = None

    @model_validator(mode="after")
    def _green_after_start(self) -> TimeSpan:
        if self.t_green is not None and self.t_green < self.t_start:
            raise ValueError("t_green cannot precede t_start")
        return self

    @property
    def duration_seconds(self) -> float | None:
        if self.t_green is None:
            return None
        return (self.t_green - self.t_start).total_seconds()


class ProofBundle(BaseModel):
    """Immutable evidence of a closed loop (§4.5 / Axiom A5)."""
    model_config = ConfigDict(frozen=True)

    pr_url: str
    commit_sha: str
    required_checks_final: list[CheckResult]
    local_gates: list[LocalGateResult] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    diff_summary: DiffSummary
    time: TimeSpan

    @property
    def all_green(self) -> bool:
        return all(c.status.is_green for c in self.required_checks_final)

    def integrity_hash(self) -> str:
        """Deterministic hash over the entire bundle for ledger anchoring."""
        payload = self.model_dump_json(indent=None).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


# ─── Loop State (engine internal) ────────────────────────────────────────────

class LoopState(BaseModel):
    """Mutable state of one canonical loop execution."""
    model_config = ConfigDict(validate_assignment=True)

    phase: Phase = Phase.OBSERVE
    iteration: int = 0
    target: TargetState
    constraints: Constraints
    active_packets: list[FailPacket] = Field(default_factory=list)
    closed_packets: list[str] = Field(default_factory=list)
    current_spec: Spec | None = None
    audit_verdict: AuditVerdict | None = None
    proof: ProofBundle | None = None
    halted: bool = False
    halt_reason: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)

    def record(self, event: str, **data: Any) -> None:
        self.history.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": self.phase.value,
            "iter": self.iteration,
            "event": event,
            **data,
        })

    def halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason
        self.phase = Phase.HALTED
        self.record("HALT", reason=reason)
