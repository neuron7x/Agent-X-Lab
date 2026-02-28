from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_contract() -> dict:
    return {
        "metadata": {
            "core_candidates": [
                {"agent_id": "A"},
                {"agent_id": "B"},
                {"agent_id": "C"},
                {"agent_id": "D"},
                {"agent_id": "E"},
            ]
        },
        "wiring": {"edges": [{"from_id": "A", "to_id": "B"}]},
        "unknowns": {"events": []},
    }


def _run_checker(tmp_path: Path, base: dict, head: dict, override: str) -> subprocess.CompletedProcess[str]:
    base_path = tmp_path / "base.json"
    head_path = tmp_path / "head.json"
    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.md"
    _write_json(base_path, base)
    _write_json(head_path, head)

    script = Path(__file__).resolve().parents[1] / "scripts" / "check_architecture_drift.py"
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--base",
            str(base_path),
            "--head",
            str(head_path),
            "--override",
            override,
            "--summary",
            str(summary_path),
            "--report",
            str(report_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_pass_when_no_new_cycles_and_no_core_degradation(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()

    proc = _run_checker(tmp_path, base, head, "false")

    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout


def test_fails_on_new_cycle_without_override(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()
    head["unknowns"]["events"] = [
        {"type": "ARCHITECTURAL_CYCLE_DETECTED", "agent_ids": ["A", "B"]}
    ]

    proc = _run_checker(tmp_path, base, head, "false")

    assert proc.returncode == 1
    assert "NEW_CYCLIC_DEPENDENCY" in proc.stderr


def test_fails_on_core_degradation_without_override(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()
    head["metadata"]["core_candidates"] = [
        {"agent_id": "A"},
        {"agent_id": "B"},
        {"agent_id": "C"},
        {"agent_id": "D"},
        {"agent_id": "Z"},
    ]

    proc = _run_checker(tmp_path, base, head, "false")

    assert proc.returncode == 1
    assert "UNAUTHORIZED_CORE_DEGRADATION" in proc.stderr


def test_allows_core_degradation_with_override(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()
    head["metadata"]["core_candidates"] = [
        {"agent_id": "A"},
        {"agent_id": "B"},
        {"agent_id": "C"},
        {"agent_id": "D"},
        {"agent_id": "Z"},
    ]

    proc = _run_checker(tmp_path, base, head, "true")

    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout
