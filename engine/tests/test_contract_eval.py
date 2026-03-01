from __future__ import annotations

from exoneural_governor.contract_eval import evaluate_contracts, validate_repo_model_schema


def test_contract_eval_runs_and_returns_structured_report() -> None:
    code, report = evaluate_contracts(strict=False, out_path=None, json_mode=False)
    assert code in {0, 2, 3}
    assert report["state"] in {"PASS", "FAIL", "ERROR"}
    assert isinstance(report["gates"], list)
    assert len(report["gates"]) >= 1


def test_determinism_gate_present_and_structured() -> None:
    code, report = evaluate_contracts(strict=False, out_path=None, json_mode=True)
    gate = next(g for g in report["gates"] if g["id"] == "GATE_05_REPO_MODEL_DETERMINISM")
    assert gate["status"] in {"PASS", "FAIL", "ERROR"}
    assert isinstance(gate["details"], dict)
    assert code in {0, 2, 3}


def test_schema_validator_rejects_malformed() -> None:
    bad = {
        "repo_root": "/tmp",
        "repo_fingerprint": "abc",
        "agents": [],
        "edges": [],
        "core_candidates": [],
        "counts": {"agents_count": 1, "edges_count": 2},
        "unknowns": {},
    }
    ok, reason = validate_repo_model_schema(bad)
    assert not ok
    assert "core_candidates_count" in reason
