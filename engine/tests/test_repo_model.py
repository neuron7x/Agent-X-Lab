from __future__ import annotations

from pathlib import Path

from exoneural_governor.repo_model import (
    build_repo_model,
    compute_betweenness,
    compute_pagerank,
    discover_repo_root,
)


def test_pagerank_is_deterministic_on_directed_graph() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [
        ("a", "b"),
        ("a", "c"),
        ("b", "c"),
        ("c", "a"),
        ("d", "c"),
    ]
    first = compute_pagerank(nodes, edges)
    second = compute_pagerank(nodes, list(reversed(edges)))
    assert first == second
    assert list(first.keys()) == sorted(nodes)


def test_betweenness_is_deterministic_on_directed_graph() -> None:
    nodes = ["a", "b", "c", "d", "e"]
    edges = [
        ("a", "b"),
        ("a", "c"),
        ("b", "d"),
        ("c", "d"),
        ("d", "e"),
    ]
    first = compute_betweenness(nodes, edges)
    second = compute_betweenness(list(reversed(nodes)), list(reversed(edges)))
    assert first == second
    assert list(first.keys()) == sorted(nodes)


def test_repo_model_smoke_current_repo() -> None:
    repo_root = discover_repo_root(Path(__file__).resolve().parent)
    model = build_repo_model(repo_root)

    assert model["repo_root"]
    counts = model["counts"]
    assert counts["agents_count"] > 0
    assert counts["edges_count"] > 0
    assert counts["core_candidates_count"] >= 5


def test_repo_model_includes_local_wiring_edges() -> None:
    repo_root = discover_repo_root(Path(__file__).resolve().parent)
    model = build_repo_model(repo_root)
    edge_types = {edge["edge_type"] for edge in model["edges"]}
    assert edge_types & {"USES_LOCAL_ACTION", "USES_ACTION_IN_ACTION", "USES_REUSABLE_WORKFLOW"}
