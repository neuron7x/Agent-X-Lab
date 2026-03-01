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
        "core_candidates_count": 5,
        "wiring": {"edges": [{"from_id": "A", "to_id": "B"}]},
        "unknowns": {"events": [], "dangling_edges": []},
    }


def _run_checker(
    tmp_path: Path,
    base: dict,
    head: dict,
    override: bool = False,
) -> subprocess.CompletedProcess[str]:
    base_path = tmp_path / "base.json"
    head_path = tmp_path / "head.json"
    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.md"
    _write_json(base_path, base)
    _write_json(head_path, head)

    script = Path(__file__).resolve().parents[1] / "scripts" / "check_architecture_drift.py"
    cmd = [
        sys.executable,
        str(script),
        "--base",
        str(base_path),
        "--head",
        str(head_path),
        "--core-k",
        "5",
        "--summary",
        str(summary_path),
        "--report",
        str(report_path),
    ]
    if override:
        cmd.append("--override")

    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_pass_when_no_new_cycles_and_no_core_degradation(tmp_path: Path) -> None:
    proc = _run_checker(tmp_path, _base_contract(), _base_contract())
    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout


def test_fails_on_new_cycle_without_override(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()
    head["unknowns"]["events"] = [
        {"type": "ARCHITECTURAL_CYCLE_DETECTED", "agent_ids": ["A", "B"]}
    ]

    proc = _run_checker(tmp_path, base, head)
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

    proc = _run_checker(tmp_path, base, head)
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

    proc = _run_checker(tmp_path, base, head, override=True)
    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout


def test_fails_on_new_dangling_edges(tmp_path: Path) -> None:
    base = _base_contract()
    head = _base_contract()
    head["unknowns"]["dangling_edges"] = [
        {
            "from_path": "a.py",
            "to_path": "b.py",
            "edge_type": "IMPORTS_PY",
        }
    ]

    proc = _run_checker(tmp_path, base, head)
    assert proc.returncode == 1
    assert "NEW_DANGLING_EDGES" in proc.stderr


def test_fails_on_invalid_schema(tmp_path: Path) -> None:
    base = {"wiring": {"edges": []}, "unknowns": {"events": []}}
    head = _base_contract()

    proc = _run_checker(tmp_path, base, head)
    assert proc.returncode == 1
    assert "INVALID_CONTRACT_SCHEMA" in proc.stderr
