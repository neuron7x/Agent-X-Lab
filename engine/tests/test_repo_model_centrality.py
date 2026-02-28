from __future__ import annotations

from engine.exoneural_governor.repo_model import (
    betweenness_centrality_brandes,
    pagerank,
)


def test_pagerank_determinism_on_synthetic_graph() -> None:
    nodes = ["a", "b", "c", "d", "e"]
    edges = [
        ("a", "b"),
        ("b", "c"),
        ("c", "a"),
        ("c", "d"),
        ("d", "e"),
        ("e", "c"),
    ]
    first = pagerank(nodes, edges)
    second = pagerank(list(reversed(nodes)), list(reversed(edges)))
    assert first == second


def test_betweenness_determinism_on_synthetic_graph() -> None:
    nodes = ["A", "B", "C", "D", "E"]
    edges = [
        ("A", "B"),
        ("B", "C"),
        ("A", "D"),
        ("D", "C"),
        ("C", "E"),
    ]
    first = betweenness_centrality_brandes(nodes, edges)
    second = betweenness_centrality_brandes(list(reversed(nodes)), list(reversed(edges)))
    assert first == second
