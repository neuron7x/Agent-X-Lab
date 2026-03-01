from __future__ import annotations

import json
from pathlib import Path

from exoneural_governor.repo_model import _core_candidate_eligible, betweenness_centrality_brandes, generate_repo_model, pagerank, write_architecture_contract


def test_pagerank_determinism() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
    assert pagerank(nodes, edges) == pagerank(list(reversed(nodes)), list(reversed(edges)))


def test_betweenness_determinism() -> None:
    nodes = ["A", "B", "C", "D", "E"]
    edges = [("A", "B"), ("B", "C"), ("A", "D"), ("D", "C"), ("C", "E")]
    assert betweenness_centrality_brandes(nodes, edges) == betweenness_centrality_brandes(list(reversed(nodes)), list(reversed(edges)))


def _fixture(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / name


def test_repo_model_fixture_a_contract_and_names(tmp_path: Path) -> None:
    repo_root = _fixture("repo_model_fixture_a")
    out = tmp_path / "repo_model.json"
    contract = tmp_path / "architecture_contract.jsonl"
    model = generate_repo_model(repo_root, out_path=out, contract_out=contract)
    write_architecture_contract(contract, model)

    assert model["counts"]["agents_count"] > 0
    assert model["unknowns"]["dangling_edges"] == []
    assert any(a["kind"] == "MAKEFILE" and a.get("name") for a in model["agents"])

    lines = [ln for ln in contract.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == model["counts"]["agents_count"]
    row = json.loads(lines[0])
    assert isinstance(row["inputs"], list)
    assert isinstance(row["outputs"], list)


def test_repo_model_fixture_b_import_edges() -> None:
    model = generate_repo_model(_fixture("repo_model_fixture_b"))
    edge_types = [e["edge_type"] for e in model["edges"]]
    assert "IMPORTS_PY" in edge_types


def test_repo_model_fixture_c_js_edges() -> None:
    model = generate_repo_model(_fixture("repo_model_fixture_c"))
    edge_types = [e["edge_type"] for e in model["edges"]]
    assert "IMPORTS_JS" in edge_types


def test_repo_model_fixture_d_discovery_and_contract(tmp_path: Path) -> None:
    repo_root = _fixture("repo_model_fixture_d")
    out = tmp_path / "rm.json"
    contract = tmp_path / "ac.jsonl"
    model = generate_repo_model(repo_root, out_path=out, contract_out=contract)
    write_architecture_contract(contract, model)
    assert model["unknowns"]["parse_failures"] == []
    assert model["counts"]["agents_count"] >= 3
    rows = [json.loads(x) for x in contract.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == len(model["agents"])
    assert all("subdomain_tags" in r for r in rows)


def test_private_engine_module_not_core_candidate() -> None:
    assert _core_candidate_eligible("engine/exoneural_governor/_exec.py") is False
    assert _core_candidate_eligible("engine/exoneural_governor/cli.py") is True
