from __future__ import annotations

import math
from pathlib import Path

from engine.exoneural_governor.repo_model import generate_repo_model, pagerank


def test_pagerank_determinism() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]
    pr1 = pagerank(nodes, edges)
    pr2 = pagerank(nodes, edges)
    assert pr1 == pr2
    assert math.isclose(sum(pr1.values()), 1.0, rel_tol=1e-9, abs_tol=1e-9)


def test_smoke_integration_on_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    model = generate_repo_model(repo_root)

    assert model["metadata"]["fingerprint_match"] is True
    assert len(model["agents"]) > 0
    assert len(model["wiring"]["edges"]) > 0
    assert len(model["metadata"]["core_candidates"]) >= 5

    for agent in model["agents"]:
        agent_id = agent["agent_id"]
        assert len(agent_id) == 12
        int(agent_id, 16)
