"""
DAO-LIFEBOOK — Data Model Layer (§4).

Strict I/O schemas. Every structure validated at construction.
Ambiguity resolves FAIL-CLOSED (Axiom A1).

v2 improvements:
  • Deterministic integrity_hash() — sorted JSON keys, stable across versions
  • Bounded history — ring buffer at 2000 entries, prevents OOM
  • Schema version — checkpoint forward-compatibility
  • Timezone enforcement — naive datetimes auto-promoted to UTC
  • GovernorAction — proper enum, not string constants
  • Structured HistoryEvent — not raw dicts
  • ProofBundle.all_green — empty checks = not proven (fail-closed)
"""

from __future__ import annotations

import hashlib
import enum
import json
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

SCHEMA_VERSION = "2026.2.0"
_MAX_HISTORY = 2000


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

    @property
    def ordinal(self) -> int:
        return list(Phase).index(self)


class AuditVerdict(str, enum.Enum):
    OK           = "ok"
    RISK         = "risk"
    NEEDS_CHANGE = "needs_change"


class GovernorAction(str, enum.Enum):
    MERGE = "merge"
    HOLD  = "hold"
    NEXT  = "next_loop"
    HALT  = "halt"


class RefactorPolicy(str, enum.Enum):
    NO_REFACTOR = "no-refactor"
    LIMITED     = "limited"
    ALLOWED     = "allowed"


class MaturityLevel(int, enum.Enum):
    M0_MANUAL       = 0
    M1_STRUCTURED   = 1
    M2_MULTI_AGENT  = 2
    M3_AUTO_HARVEST = 3
    M4_PARALLEL     = 4
    M5_PRODUCTIZED  = 5


# ─── Evidence Primitives ─────────────────────────────────────────────────────

class ArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str = ""

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if v and (len(v) != 64 or not all(c in "0123456789abcdef" for c in v)):
            raise ValueError(f"Invalid SHA-256 hex: {v!r}")
        return v

    @classmethod
    def from_file(cls, path: Path) -> ArtifactRef:
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls(path=str(path), sha256=h)


class EvidencePointer(BaseModel):
    model_config = ConfigDict(frozen=True)
    pr: str = ""
    run: str = ""
    log_anchor: str = ""


class CheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    status: CheckStatus
    run_url: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ─── §4.1 TARGET_STATE ───────────────────────────────────────────────────────

class TargetState(BaseModel):
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
                raise ValueError(f"done_when statement too vague (< 5 chars): {stmt!r}")
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
    model_config = ConfigDict(frozen=True)
    touch_allowlist: list[str] = Field(default_factory=lambda: ["*"])
    touch_denylist: list[str] = Field(default_factory=list)
    diff_budget: DiffBudget = Field(default_factory=DiffBudget)
    refactor_policy: RefactorPolicy = RefactorPolicy.NO_REFACTOR
    security_policy: SecurityPolicy = Field(default_factory=SecurityPolicy)


# ─── §4.3 FAIL_PACKET ────────────────────────────────────────────────────────

class FailPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default="", description="Auto-assigned by packetizer")
    check_name: str = Field(..., min_length=1)
    error_extract: list[str] = Field(..., min_length=1, max_length=40)
    file_line: str | None = None
    repro_cmd: str | None = None
    done_when: str = Field(..., min_length=1)
    evidence_ptr: EvidencePointer = Field(default_factory=EvidencePointer)
    severity: int = Field(default=0, ge=0)

    @field_validator("error_extract")
    @classmethod
    def _min_signal(cls, v: list[str]) -> list[str]:
        total = sum(len(line) for line in v)
        if total < 10:
            raise ValueError(f"error_extract insufficient signal ({total} < 10 chars)")
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
    timeout_seconds: float = 300.0


class Acceptance(BaseModel):
    model_config = ConfigDict(frozen=True)
    must_pass: list[str] = Field(default_factory=list)
    must_not: list[str] = Field(default_factory=list)


class Spec(BaseModel):
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
    passed: bool = False
    log_tail: str = ""


class DiffSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    files_changed: int = Field(ge=0, default=0)
    loc_delta: int = 0


class TimeSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    t_start: datetime
    t_green: datetime | None = None

    @field_validator("t_start", mode="before")
    @classmethod
    def _tz_start(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("t_green", mode="before")
    @classmethod
    def _tz_green(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

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

    schema_version: str = SCHEMA_VERSION
    pr_url: str
    commit_sha: str
    required_checks_final: list[CheckResult]
    local_gates: list[LocalGateResult] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    diff_summary: DiffSummary
    time: TimeSpan

    @property
    def all_green(self) -> bool:
        # Fail-closed: no checks means not proven
        if not self.required_checks_final:
            return False
        return all(c.status.is_green for c in self.required_checks_final)

    def integrity_hash(self) -> str:
        """Deterministic hash — sorted keys, stable separators."""
        data = self.model_dump(mode="json")
        data.pop("schema_version", None)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─── Governor Decision ───────────────────────────────────────────────────────

class GovernorDecision(BaseModel):
    """Governor (human) decision — immutable record."""
    model_config = ConfigDict(frozen=True)

    action: GovernorAction
    reason: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)

    def __repr__(self) -> str:
        return f"GovernorDecision({self.action.value!r}, {self.reason!r})"


# ─── History Event ────────────────────────────────────────────────────────────

class HistoryEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    ts: datetime
    phase: str
    iteration: int
    event: str
    data: dict[str, Any] = Field(default_factory=dict)


# ─── Loop State ──────────────────────────────────────────────────────────────

class LoopState(BaseModel):
    """
    Mutable state of one canonical loop execution.
    History bounded to _MAX_HISTORY to prevent OOM in long sessions.
    """
    model_config = ConfigDict(validate_assignment=True)

    schema_version: str = SCHEMA_VERSION
    phase: Phase = Phase.OBSERVE
    iteration: int = 0
    target: TargetState
    constraints: Constraints
    active_packets: list[FailPacket] = Field(default_factory=list)
    closed_packet_ids: list[str] = Field(default_factory=list)
    current_spec: Spec | None = None
    audit_verdict: AuditVerdict | None = None
    proof: ProofBundle | None = None
    halted: bool = False
    halt_reason: str = ""
    history: list[HistoryEvent] = Field(default_factory=list)

    def record(self, event: str, **data: Any) -> None:
        entry = HistoryEvent(
            ts=datetime.now(timezone.utc),
            phase=self.phase.value,
            iteration=self.iteration,
            event=event,
            data=data,
        )
        self.history.append(entry)
        if len(self.history) > _MAX_HISTORY:
            self.history = self.history[-_MAX_HISTORY:]

    def halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason
        self.phase = Phase.HALTED
        self.record("HALT", reason=reason)
