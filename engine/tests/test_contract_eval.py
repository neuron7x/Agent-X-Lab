from __future__ import annotations

import os
import subprocess
from pathlib import Path

from exoneural_governor.contract_eval import evaluate_contracts, validate_repo_model_schema




def _repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(proc.stdout.strip()).resolve()


def test_contract_eval_passes_on_current_repo_when_clean() -> None:
    repo_root = _repo_root()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        return

    original = Path.cwd()
    try:
        engine_root = repo_root / "engine"
        assert engine_root.exists()
        # evaluator executes repo-model via python -m exoneural_governor
        # and should be run from engine root for importability.
        os.chdir(engine_root)
        code, report = evaluate_contracts(strict=False, out_path=None, json_mode=False)
    finally:
        os.chdir(original)

    assert code == 0
    assert report["state"] == "PASS"


def test_determinism_gate_passes() -> None:
    repo_root = _repo_root()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        return

    original = Path.cwd()
    try:
        os.chdir(repo_root / "engine")
        _, report = evaluate_contracts(strict=False, out_path=None, json_mode=True)
    finally:
        os.chdir(original)

    gate = next(g for g in report["gates"] if g["id"] == "GATE_05_REPO_MODEL_DETERMINISM")
    assert gate["status"] == "PASS"
    assert gate["details"]["repo_fingerprint_equal"] is True
    assert gate["details"]["counts_equal"] is True
    assert gate["details"]["agent_ids_equal"] is True
    assert gate["details"]["edges_multiset_equal"] is True
    assert gate["details"]["core_order_equal"] is True


def test_schema_validator_rejects_malformed_minimum_dict() -> None:
    malformed = {
        "repo_root": "/tmp",
        "repo_fingerprint": "abc",
        "agents": [],
        "edges": [],
        "core_candidates": [],
        "counts": {"agents_count": 1, "edges_count": 2},
        "unknowns": {},
    }
    ok, reason = validate_repo_model_schema(malformed)
    assert ok is False
    assert "core_candidates_count" in reason
