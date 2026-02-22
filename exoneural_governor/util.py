from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import IO, Iterable, Mapping, Sequence


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


_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str | None) -> None:
    _REQUEST_ID.set(request_id)


def get_request_id() -> str:
    existing = _REQUEST_ID.get()
    if existing:
        return existing
    request_id = generate_request_id()
    _REQUEST_ID.set(request_id)
    return request_id


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "event": getattr(record, "event", record.msg),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_request_id()),
            "ts": utc_now_iso(),
        }
        fields = getattr(record, "fields", {})
        if isinstance(fields, dict):
            payload.update({k: fields[k] for k in sorted(fields)})
        return json.dumps(payload, sort_keys=True)


def setup_json_logger(name: str, *, stream: IO[str] | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    logger.info(
        event,
        extra={"event": event, "fields": fields, "request_id": get_request_id()},
    )


class MetricsEmitter:
    def __init__(self, path: Path) -> None:
        self.path = path
        ensure_dir(path.parent)

    @staticmethod
    def _latency_bucket(latency_ms: float) -> str:
        buckets = [50, 100, 250, 500, 1000]
        for bucket in buckets:
            if latency_ms <= bucket:
                return f"le_{bucket}ms"
        return "gt_1000ms"

    def emit(
        self,
        *,
        metric: str,
        status: str,
        latency_ms: float,
        gate_outcome: str,
        error: str | None = None,
    ) -> None:
        payload = {
            "error": error,
            "gate_outcome": gate_outcome,
            "latency_bucket": self._latency_bucket(latency_ms),
            "latency_ms": round(latency_ms, 3),
            "metric": metric,
            "request_id": get_request_id(),
            "status": status,
            "success": status == "success",
            "ts": utc_now_iso(),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
