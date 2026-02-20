from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = REPO_ROOT / "protocol.yaml"


def load_protocol() -> dict:
    return yaml.safe_load(PROTOCOL.read_text(encoding="utf-8")) or {}


def step_map() -> dict[str, dict]:
    data = load_protocol()
    steps = data.get("protocol_plan", [])
    return {
        step["step_id"]: step
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("step_id"), str)
    }


def test_r6_steps_have_existing_impl_paths_for_d7_d8_d9() -> None:
    steps = step_map()
    expected = {
        "P9_HARD_DETERMINISM_STAMP_R6": "D7_RACE_CONDITION_ID",
        "P10_LAZY_IMPORT_ROBUSTNESS_R6": "D8_FRAGILE_DYNAMIC_IMPORT",
        "P11_CLEAN_ROOM_ISOLATION_R6": "D9_HIDDEN_STATE_LEAK",
    }

    for step_id, deficit_id in expected.items():
        step = steps.get(step_id)
        assert step is not None, f"missing step: {step_id}"
        assert deficit_id in (step.get("fixes") or []), f"{step_id} must fix {deficit_id}"

        impl_paths = [p for p in (step.get("impl_paths") or []) if isinstance(p, str)]
        assert impl_paths, f"{step_id} must declare impl_paths"
        missing = [p for p in impl_paths if not (REPO_ROOT / p).exists()]
        assert missing == [], f"{step_id} has missing impl paths: {missing}"


def test_all_steps_have_impl_paths() -> None:
    steps = step_map()
    missing = [
        step_id
        for step_id, step in steps.items()
        if not [p for p in (step.get("impl_paths") or []) if isinstance(p, str)]
    ]
    assert missing == [], f"steps without impl_paths: {missing}"
