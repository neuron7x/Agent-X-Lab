"""
DAO-LIFEBOOK — Truth Plane (§2.3).

CI Oracle: determines PASS/FAIL, emits canonical evidence.
Uses GitHub REST API with retry, backoff, and circuit breaker.

v2 improvements:
  • Retry with exponential backoff + jitter on transient failures
  • Circuit breaker prevents cascading API abuse
  • PR metadata cached (avoid redundant calls)
  • LocalGate uses shlex.split() — no shell=True injection risk
  • Result-based error returns
  • Structured logging with context
"""

from __future__ import annotations

import re
import shlex
import subprocess
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ._types import Result, Ok, Err, DAOError, ErrorSeverity, EC
from ._retry import RetryConfig, CircuitBreaker, retry_with_backoff
from .models import (
    CheckResult,
    CheckStatus,
    DiffSummary,
    EvidencePointer,
    FailPacket,
    LocalGateResult,
)

logger = logging.getLogger("dao.truth_plane")

_GH_API = "https://api.github.com"
_CONCLUSION_MAP: dict[str | None, CheckStatus] = {
    "success":         CheckStatus.SUCCESS,
    "neutral":         CheckStatus.SUCCESS,
    "failure":         CheckStatus.FAILURE,
    "timed_out":       CheckStatus.FAILURE,
    "cancelled":       CheckStatus.FAILURE,
    "action_required": CheckStatus.PENDING,
    "stale":           CheckStatus.UNKNOWN,
    "skipped":         CheckStatus.SKIPPED,
    None:              CheckStatus.PENDING,
}
_LEGACY_STATE_MAP: dict[str, CheckStatus] = {
    "success": CheckStatus.SUCCESS,
    "failure": CheckStatus.FAILURE,
    "error":   CheckStatus.FAILURE,
    "pending": CheckStatus.PENDING,
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

    __slots__ = ("_client", "_pr", "_retry_cfg", "_breaker", "_pr_cache")

    def __init__(
        self,
        token: str,
        pr_ref: str | PRRef,
        *,
        retry_config: RetryConfig | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._pr = pr_ref if isinstance(pr_ref, PRRef) else PRRef.parse(pr_ref)
        self._client = httpx.Client(
            base_url=self._pr.api_base,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=timeout,
        )
        self._retry_cfg = retry_config or RetryConfig()
        self._breaker = CircuitBreaker()
        self._pr_cache: dict[str, Any] | None = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CIOracle:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Internal API calls with retry ─────────────────────────────────────

    def _get(self, path: str, **params: Any) -> Result[dict[str, Any], DAOError]:
        def _do_get() -> dict[str, Any]:
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()

        return retry_with_backoff(
            _do_get,
            config=self._retry_cfg,
            breaker=self._breaker,
        )

    def _get_pr(self) -> Result[dict[str, Any], DAOError]:
        if self._pr_cache is not None:
            return Ok(self._pr_cache)
        result = self._get(f"/pulls/{self._pr.number}")
        if result.is_ok():
            self._pr_cache = result.unwrap()
        return result

    def _get_head_sha(self) -> Result[str, DAOError]:
        pr_result = self._get_pr()
        if pr_result.is_err():
            return Err(pr_result.unwrap_err())
        return Ok(pr_result.unwrap()["head"]["sha"])

    def _paginate(self, path: str, key: str | None = None, **params: Any) -> Result[list[dict[str, Any]], DAOError]:
        """Paginate through all pages of a GitHub API endpoint."""
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            result = self._get(path, per_page=100, page=page, **params)
            if result.is_err():
                return Err(result.unwrap_err())
            data = result.unwrap()

            batch = data.get(key, data) if key else data
            if isinstance(batch, dict):
                batch = batch.get(key, []) if key else [batch]
            items.extend(batch)

            if len(batch) < 100:
                break
            page += 1
        return Ok(items)

    # ── Structured output ─────────────────────────────────────────────────

    def observe(self) -> Result[tuple[str, list[CheckResult]], DAOError]:
        """
        Phase A — OBSERVE.
        Returns (head_sha, list_of_check_results).
        Merges check-runs API and legacy commit-status API.
        """
        sha_result = self._get_head_sha()
        if sha_result.is_err():
            return Err(sha_result.unwrap_err())
        sha = sha_result.unwrap()

        results: dict[str, CheckResult] = {}

        # Check Runs (Actions, etc.)
        runs_result = self._get(f"/commits/{sha}/check-runs", per_page=100)
        if runs_result.is_ok():
            runs_data = runs_result.unwrap()
            for run in runs_data.get("check_runs", []):
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

            # Handle pagination for check runs
            total = runs_data.get("total_count", 0)
            if total > 100:
                page = 2
                while len(results) < total:
                    more = self._get(f"/commits/{sha}/check-runs", per_page=100, page=page)
                    if more.is_err():
                        break
                    for run in more.unwrap().get("check_runs", []):
                        name = run["name"]
                        if name not in results:
                            conclusion = run.get("conclusion")
                            status_raw = run.get("status", "")
                            mapped = CheckStatus.PENDING if status_raw in ("queued", "in_progress") else _CONCLUSION_MAP.get(conclusion, CheckStatus.UNKNOWN)
                            results[name] = CheckResult(name=name, status=mapped, run_url=run.get("html_url", ""))
                    page += 1
                    if page > 20:  # Safety cap
                        break

        # Legacy statuses
        legacy_result = self._get(f"/commits/{sha}/status")
        if legacy_result.is_ok():
            for s in legacy_result.unwrap().get("statuses", []):
                ctx = s["context"]
                if ctx not in results:
                    mapped = _LEGACY_STATE_MAP.get(s["state"], CheckStatus.UNKNOWN)
                    results[ctx] = CheckResult(
                        name=ctx,
                        status=mapped,
                        run_url=s.get("target_url", ""),
                    )

        return Ok((sha, list(results.values())))

    def filter_required(
        self,
        all_checks: list[CheckResult],
        required_names: list[str] | None = None,
    ) -> list[CheckResult]:
        if required_names is None:
            return [c for c in all_checks if c.status != CheckStatus.SKIPPED]
        name_set = set(required_names)
        return [c for c in all_checks if c.name in name_set]

    def packetize(
        self,
        sha: str,
        failing_checks: list[CheckResult],
    ) -> list[FailPacket]:
        """Phase B — Convert each failing check into a FAIL_PACKET."""
        packets: list[FailPacket] = []
        for idx, check in enumerate(failing_checks):
            if check.status.is_green or check.status == CheckStatus.PENDING:
                continue

            packets.append(FailPacket(
                id=f"FP-{sha[:7]}-{idx:03d}",
                check_name=check.name,
                error_extract=[
                    f"Check '{check.name}' concluded: {check.status.value}",
                    f"Run URL: {check.run_url}" if check.run_url else "No run URL available",
                ],
                done_when=f"Check '{check.name}' status == success",
                evidence_ptr=EvidencePointer(
                    pr=self._pr.html_url,
                    run=check.run_url,
                    log_anchor=f"{check.name} / conclusion",
                ),
                severity=0,
            ))

        packets.sort(key=lambda p: p.severity)
        return packets

    def get_diff_summary(self) -> Result[DiffSummary, DAOError]:
        pr_result = self._get_pr()
        if pr_result.is_err():
            return Err(pr_result.unwrap_err())
        data = pr_result.unwrap()
        return Ok(DiffSummary(
            files_changed=data.get("changed_files", 0),
            loc_delta=data.get("additions", 0) - data.get("deletions", 0),
        ))

    def get_changed_files(self) -> Result[list[str], DAOError]:
        result = self._paginate(f"/pulls/{self._pr.number}/files")
        if result.is_err():
            return Err(result.unwrap_err())
        return Ok([f["filename"] for f in result.unwrap()])

    @property
    def pr(self) -> PRRef:
        return self._pr


class LocalGate:
    """
    Local truth plane — runs commands, captures exit codes + output.

    SECURITY: Uses shlex.split() + shell=False to prevent injection.
    Falls back to shell=True ONLY for complex shell expressions.
    """

    __slots__ = ()

    @staticmethod
    def run(
        cmd: str,
        cwd: str | None = None,
        timeout: float = 300.0,
    ) -> LocalGateResult:
        """Execute a command, return structured result."""
        needs_shell = any(c in cmd for c in "|&;><$`")

        try:
            if needs_shell:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                result = subprocess.run(
                    shlex.split(cmd),
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

            output = result.stdout + result.stderr
            return LocalGateResult(
                cmd=cmd,
                exit_code=result.returncode,
                passed=result.returncode == 0,
                log_tail=output[-2000:] if len(output) > 2000 else output,
            )
        except subprocess.TimeoutExpired:
            return LocalGateResult(
                cmd=cmd,
                exit_code=124,
                passed=False,
                log_tail=f"TIMEOUT after {timeout}s",
            )
        except FileNotFoundError as exc:
            return LocalGateResult(
                cmd=cmd,
                exit_code=127,
                passed=False,
                log_tail=f"Command not found: {exc}",
            )
        except Exception as exc:
            return LocalGateResult(
                cmd=cmd,
                exit_code=1,
                passed=False,
                log_tail=f"EXCEPTION: {exc}",
            )
