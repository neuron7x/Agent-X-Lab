from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.config import Config
from exoneural_governor.vr import _spec_token, _work_id


def _cfg(repo_root: Path) -> Config:
    return Config(
        repo_root=repo_root,
        base_branch="main",
        allowlist_globs=["*"],
        baseline_commands=[["python", "--version"]],
        artifact_name="artifact",
        budgets={"max_files_changed": 10, "max_loc_changed": 100},
        redaction_policy_path=repo_root / "SECURITY.redaction.yml",
        evidence_root_base=repo_root / "artifacts" / "evidence",
    )


def _collision_runs() -> int:
    raw = os.environ.get("TITAN9_COLLISION_RUNS", "").strip()
    if not raw:
        raise ValueError(
            "E_NO_COLLISION_RUNS: set TITAN9_COLLISION_RUNS for collision simulation"
        )
    val = int(raw)
    if val <= 0:
        raise ValueError("E_NO_COLLISION_RUNS: TITAN9_COLLISION_RUNS must be > 0")
    return val


def _max_runtime_seconds() -> float:
    raw = os.environ.get("TITAN9_MAX_RUNTIME_SECONDS", "").strip()
    if not raw:
        raise ValueError(
            "E_NO_MAX_RUNTIME: set TITAN9_MAX_RUNTIME_SECONDS for collision simulation"
        )
    val = float(raw)
    if val <= 0:
        raise ValueError("E_NO_MAX_RUNTIME: TITAN9_MAX_RUNTIME_SECONDS must be > 0")
    return val


def test_no_git_with_build_id_produces_stable_deterministic_id(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cfg = _cfg(repo_root)

    monkeypatch.setenv("BUILD_ID", "build-123")

    first = _work_id(repo_root, cfg)
    second = _work_id(repo_root, cfg)

    assert first == second
    assert first.startswith("release-0.0.0+nogit.")
    assert re.fullmatch(r"release-0\.0\.0\+nogit\.[0-9a-f]{32}", first)


def test_no_git_and_no_build_id_raises_fail_closed_error(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cfg = _cfg(repo_root)

    monkeypatch.delenv("BUILD_ID", raising=False)

    with pytest.raises(ValueError, match="E_NO_GIT_NO_BUILD_ID"):
        _work_id(repo_root, cfg)


def test_spec_token_uses_marker_when_present(tmp_path):
    repo_root = tmp_path / "repo"
    spec = repo_root / "docs" / "SPEC.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("# heading\n titan-9   r7  protocol   spec \n", encoding="utf-8")

    assert _spec_token(repo_root) == "TITAN-9 R7 PROTOCOL SPEC"


def test_spec_token_falls_back_to_hash_without_marker(tmp_path):
    repo_root = tmp_path / "repo"
    spec = repo_root / "docs" / "SPEC.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("No marker here\n", encoding="utf-8")

    token_a = _spec_token(repo_root)
    token_b = _spec_token(repo_root)
    assert token_a == token_b
    assert re.fullmatch(r"[0-9a-f]{64}", token_a)


def test_collision_budget_requires_env(monkeypatch):
    monkeypatch.delenv("TITAN9_COLLISION_RUNS", raising=False)
    with pytest.raises(ValueError, match="E_NO_COLLISION_RUNS"):
        _collision_runs()


def test_no_git_with_distinct_build_ids_are_unique(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cfg = _cfg(repo_root)
    (repo_root / "pyproject.toml").write_text('version = "1.2.3"\n', encoding="utf-8")
    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "SPEC.md").write_text(
        "# TITAN-9 R6 Protocol Spec\n", encoding="utf-8"
    )

    monkeypatch.setenv("TITAN9_COLLISION_RUNS", "3000")
    monkeypatch.setenv("TITAN9_MAX_RUNTIME_SECONDS", "180")
    runs = _collision_runs()
    max_runtime = _max_runtime_seconds()

    started = time.monotonic()
    ids = set()
    for i in range(runs):
        monkeypatch.setenv("BUILD_ID", f"build-{i}")
        ids.add(_work_id(repo_root, cfg))

    elapsed = time.monotonic() - started
    if elapsed > max_runtime:
        raise AssertionError(
            "E_COLLISION_TEST_BUDGET_EXCEEDED: uniqueness simulation exceeded runtime budget"
        )

    assert len(ids) == runs
