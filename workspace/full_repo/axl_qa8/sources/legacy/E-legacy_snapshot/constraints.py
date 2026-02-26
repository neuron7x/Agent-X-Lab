"""
DAO-LIFEBOOK — Constraint Enforcement (Axiom A4).

Constraints are safety rails. Violations are system faults → HALT.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import PurePosixPath

from .models import Constraints, DiffSummary, RefactorPolicy


@dataclass(frozen=True, slots=True)
class Violation:
    rule: str
    detail: str
    severity: str = "halt"  # halt | warn


class ConstraintEnforcer:
    """Stateless evaluator — feed it facts, get violations."""

    __slots__ = ("_c",)

    def __init__(self, constraints: Constraints) -> None:
        self._c = constraints

    # ── Path scope ────────────────────────────────────────────────────────

    def check_path(self, path: str) -> Violation | None:
        """Return a Violation if `path` is outside allowed scope."""
        p = PurePosixPath(path)

        # Deny takes priority
        for pattern in self._c.touch_denylist:
            if fnmatch.fnmatch(str(p), pattern):
                return Violation(
                    rule="touch_denylist",
                    detail=f"Path {path!r} matches deny pattern {pattern!r}",
                )

        # Wildcard allow = everything not denied
        if self._c.touch_allowlist == ["*"]:
            return None

        for pattern in self._c.touch_allowlist:
            if fnmatch.fnmatch(str(p), pattern):
                return None

        return Violation(
            rule="touch_allowlist",
            detail=f"Path {path!r} not in allowlist {self._c.touch_allowlist}",
        )

    def check_paths(self, paths: list[str]) -> list[Violation]:
        violations: list[Violation] = []
        for p in paths:
            v = self.check_path(p)
            if v is not None:
                violations.append(v)
        return violations

    # ── Diff budget ───────────────────────────────────────────────────────

    def check_diff(self, diff: DiffSummary) -> list[Violation]:
        violations: list[Violation] = []
        budget = self._c.diff_budget

        if diff.files_changed > budget.max_files:
            violations.append(Violation(
                rule="diff_budget.max_files",
                detail=(
                    f"Files changed ({diff.files_changed}) "
                    f"exceeds budget ({budget.max_files})"
                ),
            ))

        if abs(diff.loc_delta) > budget.max_loc:
            violations.append(Violation(
                rule="diff_budget.max_loc",
                detail=(
                    f"LOC delta ({diff.loc_delta}) "
                    f"exceeds budget (±{budget.max_loc})"
                ),
            ))

        return violations

    # ── Refactor policy ───────────────────────────────────────────────────

    def check_refactor(self, has_refactor: bool) -> Violation | None:
        if has_refactor and self._c.refactor_policy == RefactorPolicy.NO_REFACTOR:
            return Violation(
                rule="refactor_policy",
                detail="Refactoring detected under no-refactor policy",
            )
        return None

    # ── Security policy ───────────────────────────────────────────────────

    def check_security(
        self,
        *,
        disabled_checks: list[str] | None = None,
        unpinned_actions: list[str] | None = None,
        unpinned_deps: list[str] | None = None,
    ) -> list[Violation]:
        violations: list[Violation] = []
        sp = self._c.security_policy

        if sp.no_disable_security_checks and disabled_checks:
            violations.append(Violation(
                rule="security.no_disable_security_checks",
                detail=f"Disabled security checks: {disabled_checks}",
            ))

        if sp.actions_must_be_pinned and unpinned_actions:
            violations.append(Violation(
                rule="security.actions_must_be_pinned",
                detail=f"Unpinned GH actions: {unpinned_actions}",
            ))

        if sp.dependencies_must_be_pinned and unpinned_deps:
            violations.append(Violation(
                rule="security.dependencies_must_be_pinned",
                detail=f"Unpinned dependencies: {unpinned_deps}",
            ))

        return violations

    # ── Full sweep ────────────────────────────────────────────────────────

    def enforce_all(
        self,
        touched_paths: list[str],
        diff: DiffSummary,
        has_refactor: bool = False,
        disabled_checks: list[str] | None = None,
        unpinned_actions: list[str] | None = None,
        unpinned_deps: list[str] | None = None,
    ) -> list[Violation]:
        """Run every constraint check. Any non-empty result means HALT."""
        vs: list[Violation] = []
        vs.extend(self.check_paths(touched_paths))
        vs.extend(self.check_diff(diff))

        r = self.check_refactor(has_refactor)
        if r:
            vs.append(r)

        vs.extend(self.check_security(
            disabled_checks=disabled_checks,
            unpinned_actions=unpinned_actions,
            unpinned_deps=unpinned_deps,
        ))
        return vs
