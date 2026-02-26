#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _tail_40_lines(text: str) -> str:
    lines = text.splitlines()
    tail = lines[-40:]
    return "\n".join(tail)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a command and append deterministic evidence JSONL."
    )
    parser.add_argument(
        "--cwd", default=".", help="Working directory for command execution"
    )
    parser.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
    parser.add_argument("--note", default="", help="Optional short note")
    parser.add_argument(
        "--expect-path",
        action="append",
        default=[],
        help="Path expected to exist after command; can be provided multiple times.",
    )
    parser.add_argument(
        "cmd", nargs=argparse.REMAINDER, help="Command to execute (prefix with --)"
    )

    args = parser.parse_args()
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("No command provided. Use: run_and_log.py -- <command> ...")

    cwd_path = Path(args.cwd).resolve()
    cwd_path.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    completed = None
    timed_out = False
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = _ensure_text(exc.stdout)
        stderr = _ensure_text(exc.stderr) + "\n[run_and_log] timeout exceeded"

    duration = round(time.monotonic() - start, 3)

    stdout_tail = _tail_40_lines(stdout)
    stderr_tail = _tail_40_lines(stderr)

    produced_paths: list[str] = []
    for rel in args.expect_path:
        p = (cwd_path / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
        if p.exists():
            try:
                produced_paths.append(str(p.relative_to(Path.cwd())))
            except ValueError:
                produced_paths.append(str(p))

    record = {
        "ts_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "cmd": cmd,
        "cwd": str(cwd_path),
        "exit": exit_code,
        "duration_s": duration,
        "stdout_tail_sha256": _sha256_text(stdout_tail),
        "stderr_tail_sha256": _sha256_text(stderr_tail),
        "produced_paths": produced_paths,
        "notes": args.note[:280] if args.note else ("timeout" if timed_out else ""),
    }

    evidence_path = Path("artifacts/agent/evidence.jsonl")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
