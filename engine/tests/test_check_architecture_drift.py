from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_architecture_drift.py"
SPEC = importlib.util.spec_from_file_location("check_architecture_drift", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _model(core: list[str], cycles: list[list[str]], edge_count: int) -> dict:
    return {
        "metadata": {"core_candidates": [{"agent_id": aid} for aid in core]},
        "unknowns": [{"type": "ARCHITECTURAL_CYCLE_DETECTED", "agent_ids": c} for c in cycles],
        "wiring": {"edges": [{"source": "a", "target": "b"}] * edge_count},
    }


def test_fails_when_new_cycle_or_core_displacement_without_override() -> None:
    base = _model(core=["A", "B", "C", "D", "E"], cycles=[], edge_count=3)
    head = _model(core=["A", "B", "C", "D", "X"], cycles=[["A", "B"]], edge_count=4)

    fatal, report = MODULE.render_report(base, head, has_override=False)

    assert "NEW_CYCLIC_DEPENDENCY" in fatal
    assert "UNAUTHORIZED_CORE_DEGRADATION" in fatal
    assert any("Verdict" in line for line in report)


def test_allows_core_displacement_with_override() -> None:
    base = _model(core=["A", "B", "C", "D", "E"], cycles=[], edge_count=3)
    head = _model(core=["A", "B", "C", "D", "X"], cycles=[], edge_count=2)

    fatal, report = MODULE.render_report(base, head, has_override=True)

    assert fatal == []
    assert any("Override label active: **True**" in line for line in report)
