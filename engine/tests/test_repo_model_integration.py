from __future__ import annotations

from pathlib import Path

from exoneural_governor.repo_model import generate_repo_model


def test_smoke_repo_model_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    model = generate_repo_model(repo_root)

    assert Path(model["repo_root"]).resolve() == repo_root
    assert model["agents_count"] > 0
    assert model["wiring"]["edges_count"] > 0
    assert model["core_candidates_count"] >= 5
