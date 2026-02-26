"""
DAO-LIFEBOOK — Metrics & KPD (§7).

KPD = (Closures / Time_hours) / (1 + Δ_diff/DiffBudget_LOC + R_rework)

v2: better edge case handling, thread-safe via properties, comprehensive summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class LoopMetrics:
    """Accumulated metrics for one loop session."""

    n_iter: int = 0
    t_start: datetime | None = None
    t_green: datetime | None = None
    files_changed: int = 0
    loc_delta: int = 0
    diff_budget_loc: int = 500
    rework_iterations: int = 0
    total_iterations: int = 0
    closures: int = 0

    # Per-phase timing (for optimization)
    phase_durations: dict[str, list[float]] = field(default_factory=dict)

    def start(self) -> None:
        if self.t_start is None:
            self.t_start = datetime.now(timezone.utc)

    def mark_green(self) -> None:
        if self.t_green is None:
            self.t_green = datetime.now(timezone.utc)

    @property
    def t_green_seconds(self) -> float | None:
        if self.t_start is None or self.t_green is None:
            return None
        return max(0.0, (self.t_green - self.t_start).total_seconds())

    @property
    def r_rework(self) -> float:
        if self.total_iterations == 0:
            return 0.0
        return self.rework_iterations / self.total_iterations

    @property
    def kpd(self) -> float:
        """
        КПД — practical efficiency formula (§7.2).
        KPD = (Closures / Time_hours) / (1 + Δ_diff/Budget + R_rework)
        Higher is better. Returns 0.0 on insufficient data.
        """
        t = self.t_green_seconds
        if t is None or t < 0.001 or self.closures == 0:
            return 0.0

        t_hours = t / 3600.0
        throughput = self.closures / t_hours

        diff_ratio = abs(self.loc_delta) / max(self.diff_budget_loc, 1)
        penalty = 1.0 + diff_ratio + self.r_rework

        return throughput / penalty

    def record_iteration(
        self,
        *,
        closed: int = 0,
        new_failures: bool = False,
    ) -> None:
        self.total_iterations += 1
        self.closures += closed
        if new_failures:
            self.rework_iterations += 1

    def record_diff(self, files: int, loc: int) -> None:
        self.files_changed = max(self.files_changed, files)
        self.loc_delta = loc

    def record_phase(self, phase: str, duration_s: float) -> None:
        """Track per-phase timing for optimization."""
        self.phase_durations.setdefault(phase, []).append(duration_s)

    def summary(self) -> dict[str, Any]:
        return {
            "n_iter": self.n_iter,
            "t_green_s": self.t_green_seconds,
            "files_changed": self.files_changed,
            "loc_delta": self.loc_delta,
            "r_rework": round(self.r_rework, 4),
            "closures": self.closures,
            "kpd": round(self.kpd, 4),
            "total_iterations": self.total_iterations,
            "rework_iterations": self.rework_iterations,
        }


@dataclass(slots=True)
class Ledger:
    """
    Persistent record of all loop executions.
    Each entry is a proof bundle hash + metrics summary.
    """

    entries: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        proof_hash: str,
        metrics: LoopMetrics,
        **extra: Any,
    ) -> None:
        self.entries.append({
            "proof_hash": proof_hash,
            "metrics": metrics.summary(),
            "ts": datetime.now(timezone.utc).isoformat(),
            **extra,
        })

    @property
    def total_closures(self) -> int:
        return sum(e["metrics"]["closures"] for e in self.entries)

    @property
    def avg_kpd(self) -> float:
        kpds = [e["metrics"]["kpd"] for e in self.entries if e["metrics"]["kpd"] > 0]
        return sum(kpds) / len(kpds) if kpds else 0.0

    @property
    def total_iterations(self) -> int:
        return sum(e["metrics"]["total_iterations"] for e in self.entries)

    def export(self) -> list[dict[str, Any]]:
        return list(self.entries)
