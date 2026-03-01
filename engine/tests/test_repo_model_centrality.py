from __future__ import annotations

from exoneural_governor.repo_model import betweenness_centrality_brandes, pagerank


def _top5(nodes: list[str], edges: list[tuple[str, str]]) -> list[str]:
    pr = pagerank(nodes, edges)
    bc = betweenness_centrality_brandes(nodes, edges)
    scored = sorted(((n, 0.6 * pr.get(n, 0.0) + 0.4 * bc.get(n, 0.0)) for n in nodes), key=lambda x: (-x[1], x[0]))
    return [n for n, _ in scored[:5]]


def test_centrality_stability_with_isolated_nodes() -> None:
    nodes = ["a", "b", "c", "d", "e", "f"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"), ("d", "e"), ("e", "f")]
    t1 = _top5(nodes, edges)
    t2 = _top5(nodes + [f"iso{i}" for i in range(8)], edges)
    assert t1[0] == t2[0]
