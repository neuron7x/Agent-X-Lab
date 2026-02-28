from __future__ import annotations

from engine.exoneural_governor.repo_model import betweenness_centrality_brandes


def test_brandes_bridge_node_normalizes_to_one() -> None:
    nodes = ["A", "B", "C"]
    edges = [("A", "B"), ("B", "C")]
    bc = betweenness_centrality_brandes(nodes, edges)
    max_bc = max(bc.values())
    assert max_bc > 0.0
    norm_b = bc["B"] / max_bc
    assert norm_b == 1.0
