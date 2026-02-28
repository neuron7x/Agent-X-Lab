from __future__ import annotations

from pathlib import Path

from exoneural_governor.repo_model import (
    betweenness_centrality_brandes,
    generate_repo_model,
    pagerank,
)


def test_pagerank_determinism() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
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
