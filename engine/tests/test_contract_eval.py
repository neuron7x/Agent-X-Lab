from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from exoneural_governor.contract_eval import evaluate_contracts, validate_repo_model_schema


def _repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True)
    return Path(proc.stdout.strip()).resolve()


def test_contract_eval_runs(tmp_path: Path) -> None:
    repo_root = _repo_root()
    original = Path.cwd()
    try:
        os.chdir(repo_root / "engine")
        code, report = evaluate_contracts(strict=False, out_path=tmp_path, json_mode=True, no_write=True)
    finally:
        os.chdir(original)
    assert code in (0, 2)
    ids = [g["id"] for g in report["gates"]]
    assert "GATE_A01_ENVIRONMENT_STAMP" in ids
    assert "GATE_A03_DETERMINISTIC_ENV_STAMP" in ids
    assert (tmp_path / "report.json").exists()


def test_contract_eval_gate_ids_unique(tmp_path: Path) -> None:
    repo_root = _repo_root()
    original = Path.cwd()
    try:
        os.chdir(repo_root / "engine")
        _, report = evaluate_contracts(strict=False, out_path=tmp_path, json_mode=True, no_write=True)
    finally:
        os.chdir(original)
    ids = [g["id"] for g in report["gates"]]
    assert len(ids) == len(set(ids))


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
