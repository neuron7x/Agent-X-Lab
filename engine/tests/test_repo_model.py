from __future__ import annotations

import json
from pathlib import Path

from exoneural_governor.repo_model import (
    betweenness_centrality_brandes,
    generate_repo_model,
    write_architecture_contract,
)


def test_pagerank_determinism() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
    from exoneural_governor.repo_model import pagerank

    assert pagerank(nodes, edges) == pagerank(list(reversed(nodes)), list(reversed(edges)))


def test_betweenness_determinism() -> None:
    nodes = ["A", "B", "C", "D", "E"]
    edges = [("A", "B"), ("B", "C"), ("A", "D"), ("D", "C"), ("C", "E")]
    assert betweenness_centrality_brandes(nodes, edges) == betweenness_centrality_brandes(
        list(reversed(nodes)), list(reversed(edges))
    )


def test_repo_model_smoke_and_local_action_edges() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    model = generate_repo_model(repo_root)

    assert Path(model["repo_root"]).resolve() == repo_root
    assert model["agents_count"] > 0
    assert model["wiring"]["edges_count"] > 0
    assert model["core_candidates_count"] >= 5

    edge_types = {edge["edge_type"] for edge in model["wiring"]["edges"]}
    assert {
        "USES_LOCAL_ACTION",
        "USES_ACTION_IN_ACTION",
        "USES_REUSABLE_WORKFLOW",
    } & edge_types


def test_repo_model_import_edges_and_nonzero_bc() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    model = generate_repo_model(repo_root)

    edges = model["wiring"]["edges"]
    import_edges = [edge for edge in edges if edge["edge_type"] == "IMPORTS_PY"]
    assert import_edges

    bc_values = list(model["centrality"]["betweenness"].values())
    assert max(bc_values) > 0.0


def test_repo_model_quality_and_contract(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out = tmp_path / "repo_model.json"
    contract = tmp_path / "architecture_contract.jsonl"
    model = generate_repo_model(repo_root, out_path=out, contract_out=contract)
    write_architecture_contract(contract, model)

    assert model["unknowns"]["dangling_edges"] == []

    named = [a for a in model["agents"] if a.get("name") is not None]
    assert (len(named) / max(1, len(model["agents"]))) >= 0.8

    py_with_args = [
        a
        for a in model["agents"]
        if a["path"].endswith(".py")
        and any(inp.get("source") == "python:argparse" for inp in a.get("interface", {}).get("inputs", []))
    ]
    assert py_with_args
    assert len(py_with_args[0]["interface"]["inputs"]) > 0

    lines = [ln for ln in contract.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines
    obj = json.loads(lines[0])
    assert "agent_id" in obj
    assert "inputs" in obj and isinstance(obj["inputs"], list)
    assert "outputs" in obj and isinstance(obj["outputs"], list)
    assert "core_rank" in obj
