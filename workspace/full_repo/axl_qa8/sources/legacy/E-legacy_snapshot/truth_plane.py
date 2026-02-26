"""
DAO-LIFEBOOK — Truth Plane (§2.3).

CI Oracle: determines PASS/FAIL, emits canonical evidence.
Uses GitHub REST API for check-runs and check-suites.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from .models import (
    CheckResult,
    CheckStatus,
    EvidencePointer,
    FailPacket,
    DiffSummary,
)

logger = logging.getLogger("dao.truth_plane")

_GH_API = "https://api.github.com"
_CONCLUSION_MAP: dict[str | None, CheckStatus] = {
    "success":          CheckStatus.SUCCESS,
    "neutral":          CheckStatus.SUCCESS,
    "failure":          CheckStatus.FAILURE,
    "timed_out":        CheckStatus.FAILURE,
    "cancelled":        CheckStatus.FAILURE,
    "action_required":  CheckStatus.PENDING,
    "stale":            CheckStatus.UNKNOWN,
    "skipped":          CheckStatus.SKIPPED,
    None:               CheckStatus.PENDING,
}


@dataclass(frozen=True, slots=True)
class PRRef:
    """Parsed owner/repo#number."""
    owner: str
    repo: str
    number: int

    @classmethod
    def parse(cls, url_or_ref: str) -> PRRef:
        """
        Accepts:
          - https://github.com/owner/repo/pull/123
          - owner/repo#123
        """
        m = re.match(
            r"(?:https?://github\.com/)?([^/]+)/([^/#]+)(?:/pull/|#)(\d+)",
            url_or_ref.strip(),
        )
        if not m:
            raise ValueError(f"Cannot parse PR reference: {url_or_ref!r}")
        return cls(owner=m.group(1), repo=m.group(2), number=int(m.group(3)))

    @property
    def api_base(self) -> str:
        return f"{_GH_API}/repos/{self.owner}/{self.repo}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}"


class CIOracle:
    """
    Read-only interface to the Truth Plane.

    Axiom A1: Truth = Required Checks status + canonical logs.
    This class ONLY reads; it never mutates repository state.
    """

    __slots__ = ("_client", "_pr")

    def __init__(self, token: str, pr_ref: str | PRRef) -> None:
        self._pr = pr_ref if isinstance(pr_ref, PRRef) else PRRef.parse(pr_ref)
        self._client = httpx.Client(
            base_url=self._pr.api_base,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CIOracle:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Raw data ──────────────────────────────────────────────────────────

    def _get_pr(self) -> dict[str, Any]:
        resp = self._client.get(f"/pulls/{self._pr.number}")
        resp.raise_for_status()
        return resp.json()

    def _get_head_sha(self) -> str:
        pr_data = self._get_pr()
        return pr_data["head"]["sha"]

    def _get_check_runs(self, sha: str) -> list[dict[str, Any]]:
        """Paginate through all check runs for a commit."""
        runs: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = self._client.get(
                f"/commits/{sha}/check-runs",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("check_runs", [])
            runs.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return runs

    def _get_combined_status(self, sha: str) -> list[dict[str, Any]]:
        """Legacy commit statuses (some CI systems use these)."""
        resp = self._client.get(f"/commits/{sha}/status")
        resp.raise_for_status()
        return resp.json().get("statuses", [])

    def _get_diff_stat(self) -> DiffSummary:
        resp = self._client.get(f"/pulls/{self._pr.number}")
        resp.raise_for_status()
        data = resp.json()
        return DiffSummary(
            files_changed=data.get("changed_files", 0),
            loc_delta=data.get("additions", 0) - data.get("deletions", 0),
        )

    def _get_changed_files(self) -> list[str]:
        files: list[str] = []
        page = 1
        while True:
            resp = self._client.get(
                f"/pulls/{self._pr.number}/files",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            files.extend(f["filename"] for f in batch)
            if len(batch) < 100:
                break
            page += 1
        return files

    # ── Structured output ─────────────────────────────────────────────────

    def observe(self) -> tuple[str, list[CheckResult]]:
        """
        Phase A — OBSERVE.

        Returns (head_sha, list_of_check_results).
        Merges both check-runs API and legacy commit-status API.
        """
        sha = self._get_head_sha()
        results: dict[str, CheckResult] = {}

        # Check Runs (Actions, etc.)
        for run in self._get_check_runs(sha):
            name = run["name"]
            conclusion = run.get("conclusion")
            status_raw = run.get("status", "")

            if status_raw in ("queued", "in_progress"):
                mapped = CheckStatus.PENDING
            else:
                mapped = _CONCLUSION_MAP.get(conclusion, CheckStatus.UNKNOWN)

            results[name] = CheckResult(
                name=name,
                status=mapped,
                run_url=run.get("html_url", ""),
            )

        # Legacy statuses
        for s in self._get_combined_status(sha):
            ctx = s["context"]
            if ctx not in results:
                state = s["state"]
                mapped = {
                    "success": CheckStatus.SUCCESS,
                    "failure": CheckStatus.FAILURE,
                    "error":   CheckStatus.FAILURE,
                    "pending": CheckStatus.PENDING,
                }.get(state, CheckStatus.UNKNOWN)
                results[ctx] = CheckResult(
                    name=ctx,
                    status=mapped,
                    run_url=s.get("target_url", ""),
                )

        return sha, list(results.values())

    def filter_required(
        self,
        all_checks: list[CheckResult],
        required_names: list[str] | None = None,
    ) -> list[CheckResult]:
        """
        Filter to only required checks.

        If required_names is None (auto-detect), returns all non-skipped checks.
        """
        if required_names is None:
            return [c for c in all_checks if c.status != CheckStatus.SKIPPED]
        name_set = set(required_names)
        return [c for c in all_checks if c.name in name_set]

    def packetize(
        self,
        sha: str,
        failing_checks: list[CheckResult],
    ) -> list[FailPacket]:
        """
        Phase B — PACKETIZE.

        Convert each failing check into a FAIL_PACKET with evidence pointers.
        Error extraction requires run log access; we provide the anchor.
        """
        packets: list[FailPacket] = []
        for idx, check in enumerate(failing_checks):
            if check.status.is_green or check.status == CheckStatus.PENDING:
                continue

            packets.append(FailPacket(
                id=f"FP-{sha[:7]}-{idx:03d}",
                check_name=check.name,
                error_extract=[
                    f"Check '{check.name}' concluded with status: {check.status.value}",
                    f"Run URL: {check.run_url}",
                ],
                done_when=f"Check '{check.name}' status == success",
                evidence_ptr=EvidencePointer(
                    pr=self._pr.html_url,
                    run=check.run_url,
                    log_anchor=f"{check.name} / conclusion",
                ),
                severity=0,
            ))

        # Sort by severity (0 = blocking first)
        packets.sort(key=lambda p: p.severity)
        return packets

    def get_diff_summary(self) -> DiffSummary:
        return self._get_diff_stat()

    def get_changed_files(self) -> list[str]:
        return self._get_changed_files()

    @property
    def pr(self) -> PRRef:
        return self._pr


class LocalGate:
    """
    Local truth plane — runs commands and captures exit codes + output.

    Supplements CI for fast feedback before push.
    """

    __slots__ = ()

    @staticmethod
    def run(cmd: str, cwd: str | None = None, timeout: float = 300.0) -> tuple[int, str]:
        """
        Execute a command, return (exit_code, combined_output).

        Does NOT interpret results — that's the engine's job.
        """
        import subprocess

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return 124, f"TIMEOUT after {timeout}s: {cmd}"
        except Exception as exc:
            return 1, f"EXCEPTION: {exc}"
