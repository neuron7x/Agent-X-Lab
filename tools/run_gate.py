#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gate-id", required=True)
    p.add_argument("--cwd", default=".")
    p.add_argument("--stdout", type=Path, required=True)
    p.add_argument("--stderr", type=Path, required=True)
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    args = p.parse_args()

    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        p.error("missing command; provide after --")

    cwd = Path(args.cwd).resolve()
    args.stdout.parent.mkdir(parents=True, exist_ok=True)
    args.stderr.parent.mkdir(parents=True, exist_ok=True)

    start_ts = _iso_now()
    start = time.monotonic()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    duration = round(time.monotonic() - start, 3)
    end_ts = _iso_now()

    args.stdout.write_text(result.stdout, encoding="utf-8")
    args.stderr.write_text(result.stderr, encoding="utf-8")

    artifacts: list[dict[str, object]] = []
    for item in args.artifact:
        path = Path(item)
        full = path if path.is_absolute() else (cwd / path)
        exists = full.exists()
        entry: dict[str, object] = {"path": str(path), "exists": exists}
        if exists and full.is_file():
            entry["sha256"] = _sha256(full)
        artifacts.append(entry)

    record = {
        "gate_id": args.gate_id,
        "command": cmd,
        "cwd": str(cwd),
        "start_utc": start_ts,
        "end_utc": end_ts,
        "duration_s": duration,
        "exit_code": result.returncode,
        "stdout_path": str(args.stdout),
        "stderr_path": str(args.stderr),
        "artifacts": artifacts,
    }

    ev = Path("artifacts/agent/evidence.jsonl")
    ev.parent.mkdir(parents=True, exist_ok=True)
    with ev.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=__import__("sys").stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
