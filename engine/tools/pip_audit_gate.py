#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from importlib import metadata
from pathlib import Path


@dataclass(frozen=True)
class AllowEntry:
    vuln_id: str
    reason: str
    expires: date


def _parse_expiry(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"invalid expires date '{raw}', expected YYYY-MM-DD") from exc


def _load_allowlist(path: Path) -> list[AllowEntry]:
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    ignore = payload.get("ignore", [])
    if not isinstance(ignore, list):
        raise ValueError("allowlist must contain an 'ignore' array")

    parsed: list[AllowEntry] = []
    for item in ignore:
        if not isinstance(item, dict):
            raise ValueError("allowlist entries must be objects")
        vuln_id = str(item.get("id", "")).strip()
        reason = str(item.get("reason", "")).strip()
        expires_raw = str(item.get("expires", "")).strip()
        if not vuln_id or not reason or not expires_raw:
            raise ValueError("allowlist entry requires id, reason, expires")
        parsed.append(
            AllowEntry(
                vuln_id=vuln_id, reason=reason, expires=_parse_expiry(expires_raw)
            )
        )
    return parsed


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _pip_audit_version() -> str | None:
    try:
        return metadata.version("pip-audit")
    except metadata.PackageNotFoundError:
        return None


def _error_envelope(
    *,
    reason_code: str,
    remediation: str,
    detail: str,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    version: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "error",
        "tool": "pip-audit",
        "version": version,
        "reason_code": reason_code,
        "remediation": remediation,
        "reason": reason_code,
        "detail": detail,
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    if stdout:
        payload["stdout"] = stdout
    if stderr:
        payload["stderr"] = stderr
    return payload


def _fail_report(
    path: Path,
    reason_code: str,
    detail: str,
    remediation: str,
    exit_code: int,
    *,
    version: str | None = None,
) -> int:
    _write_report(
        path,
        _error_envelope(
            reason_code=reason_code,
            remediation=remediation,
            detail=detail,
            exit_code=exit_code,
            version=version,
        ),
    )
    print(f"FAIL: {detail}")
    return exit_code


def _split_allowlist(
    entries: list[AllowEntry], today: date
) -> tuple[list[str], list[str]]:
    active: list[str] = []
    expired: list[str] = []
    for entry in entries:
        descriptor = f"{entry.vuln_id} (expires={entry.expires.isoformat()}, reason={entry.reason})"
        if entry.expires < today:
            expired.append(descriptor)
            continue
        active.append(entry.vuln_id)
    return active, expired


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", action="append", required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    force_missing = str(
        __import__("os").environ.get("PIP_AUDIT_FORCE_MISSING", "")
    ).lower() in {"1", "true", "yes"}

    try:
        entries = _load_allowlist(args.allowlist)
    except Exception as exc:
        return _fail_report(
            args.out,
            "allowlist-parse-error",
            str(exc),
            "fix policies/pip_audit_allowlist.json format",
            4,
            version=None,
        )

    today = datetime.now(timezone.utc).date()
    active_ignores, expired = _split_allowlist(entries, today)
    if expired:
        _write_report(
            args.out,
            {
                **_error_envelope(
                    reason_code="allowlist-expired",
                    remediation="refresh or remove expired allowlist entries",
                    detail="expired vulnerability allowlist entries detected",
                    exit_code=2,
                    version=None,
                ),
                "expired_entries": expired,
            },
        )
        print("FAIL: expired vulnerability allowlist entries detected:")
        for line in expired:
            print(f"  - {line}")
        return 2

    pip_audit_version = None if force_missing else _pip_audit_version()
    if force_missing or pip_audit_version is None:
        return _fail_report(
            args.out,
            "pip-audit-missing",
            "pip-audit is not installed. Run `python -m pip install pip-audit==2.9.0`.",
            "install pip-audit==2.9.0",
            3,
            version=None,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "--format",
        "json",
        "--output",
        str(args.out),
    ]
    for req in args.requirements:
        cmd.extend(["-r", req])
    for vuln_id in active_ignores:
        cmd.extend(["--ignore-vuln", vuln_id])

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        combined = (proc.stdout or "") + (proc.stderr or "")
        if "No module named pip_audit" in combined:
            return _fail_report(
                args.out,
                "pip-audit-missing",
                "pip-audit is not installed. Run `python -m pip install pip-audit==2.9.0`.",
                "install pip-audit==2.9.0",
                3,
                version=None,
            )
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.stderr:
            print(proc.stderr.rstrip())
        if not args.out.exists():
            _write_report(
                args.out,
                _error_envelope(
                    reason_code="pip-audit-failed",
                    remediation="review stderr/stdout and fix vulnerable dependencies",
                    detail="pip-audit exited non-zero and did not produce a report",
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    version=None,
                ),
            )
        print(
            "FAIL: dependency vulnerabilities found; see "
            f"{args.out.as_posix()} for full report."
        )
        return proc.returncode

    if not args.out.exists():
        _write_report(
            args.out,
            _error_envelope(
                reason_code="pip-audit-missing-report",
                remediation="rerun pip-audit with --format json --output <path>",
                detail="pip-audit succeeded but did not write JSON output",
                exit_code=5,
                version=None,
            ),
        )
        print(
            "FAIL: pip-audit did not write expected JSON output; "
            f"created envelope report at {args.out.as_posix()}."
        )
        return 5

    print(
        f"PASS: dependency vulnerability audit succeeded; report={args.out.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
