from __future__ import annotations

import io
import json
from pathlib import Path

from exoneural_governor.util import (
    MetricsEmitter,
    log_event,
    set_request_id,
    setup_json_logger,
)


def test_structured_log_contains_required_fields() -> None:
    stream = io.StringIO()
    logger = setup_json_logger("tests.observability", stream=stream)
    set_request_id("req-smoke-001")

    log_event(logger, "smoke.event", command="inventory", gate_outcome="success")

    payload = json.loads(stream.getvalue().strip())
    for key in ("event", "level", "logger", "message", "request_id", "ts"):
        assert key in payload
    assert payload["request_id"] == "req-smoke-001"
    assert payload["gate_outcome"] == "success"


def test_metrics_emitter_contains_required_fields(tmp_path: Path) -> None:
    set_request_id("req-smoke-002")
    out = tmp_path / "metrics.jsonl"
    emitter = MetricsEmitter(out)

    emitter.emit(
        metric="sg.command",
        status="success",
        latency_ms=12.2,
        gate_outcome="success",
    )

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    for key in (
        "error",
        "gate_outcome",
        "latency_bucket",
        "latency_ms",
        "metric",
        "request_id",
        "status",
        "success",
        "ts",
    ):
        assert key in payload
    assert payload["request_id"] == "req-smoke-002"
    assert payload["status"] == "success"
    assert payload["success"] is True
