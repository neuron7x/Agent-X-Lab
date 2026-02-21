#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
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


def _fail_report(path: Path, reason: str, detail: str, exit_code: int) -> int:
    _write_report(path, {"status": "error", "reason": reason, "detail": detail})
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

    try:
        entries = _load_allowlist(args.allowlist)
    except Exception as exc:
        return _fail_report(args.out, "allowlist_parse_error", str(exc), 4)

    today = datetime.now(timezone.utc).date()
    active_ignores, expired = _split_allowlist(entries, today)
    if expired:
        _write_report(
            args.out,
            {
                "status": "error",
                "reason": "expired_allowlist",
                "expired_entries": expired,
            },
        )
        print("FAIL: expired vulnerability allowlist entries detected:")
        for line in expired:
            print(f"  - {line}")
        return 2

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
                "pip_audit_missing",
                "pip-audit is not installed. Run `python -m pip install pip-audit==2.9.0`.",
                3,
            )
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.stderr:
            print(proc.stderr.rstrip())
        if not args.out.exists():
            _write_report(
                args.out,
                {
                    "status": "error",
                    "reason": "pip_audit_failed_without_report",
                    "exit": proc.returncode,
                    "stderr": proc.stderr,
                    "stdout": proc.stdout,
                },
            )
        print(
            "FAIL: dependency vulnerabilities found; see "
            f"{args.out.as_posix()} for full report."
        )
        return proc.returncode

    if not args.out.exists():
        _write_report(args.out, {"status": "ok", "dependencies": []})

    print(
        f"PASS: dependency vulnerability audit succeeded; report={args.out.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
