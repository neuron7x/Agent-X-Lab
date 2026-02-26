from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class CmdResult:
    argv: list[str]
    cwd: str
    exit_code: int
    stdout_path: str
    stderr_path: str


def run_cmd(
    argv: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: Mapping[str, str] | None = None,
) -> CmdResult:
    """Run a command deterministically: no shell, explicit argv, captured stdout/stderr.
    Caller decides policy on non-zero exit codes."""
    ensure_dir(stdout_path.parent)
    ensure_dir(stderr_path.parent)

    proc = subprocess.run(
        list(argv),
        cwd=str(cwd),
        env=dict(os.environ, **(env or {})),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        check=False,
    )
    stdout_path.write_bytes(proc.stdout or b"")
    stderr_path.write_bytes(proc.stderr or b"")
    return CmdResult(
        argv=list(argv),
        cwd=str(cwd),
        exit_code=int(proc.returncode),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )


def redact_bytes(data: bytes, patterns: Iterable[str]) -> bytes:
    # Byte-safe redaction: apply patterns on decoded text with replacement markers.
    text = data.decode("utf-8", errors="replace")
    for pat in patterns:
        try:
            text = re.sub(pat, "[REDACTED]", text)
        except re.error:
            # Fail-closed: invalid regex is a configuration defect.
            raise ValueError(f"Invalid redaction regex: {pat!r}")
    return text.encode("utf-8")


def write_json(path: Path, obj) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
