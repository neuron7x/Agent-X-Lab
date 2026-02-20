from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.config import Config
from exoneural_governor.vr import _work_id


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


def test_no_git_with_build_id_produces_stable_deterministic_id(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cfg = _cfg(repo_root)

    monkeypatch.setenv("BUILD_ID", "build-123")

    first = _work_id(repo_root, cfg)
    second = _work_id(repo_root, cfg)

    assert first == second
    assert len(first) >= 32
    assert re.fullmatch(r"[0-9a-f]{32}", first)


def test_no_git_and_no_build_id_raises_fail_closed_error(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cfg = _cfg(repo_root)

    monkeypatch.delenv("BUILD_ID", raising=False)

    try:
        _work_id(repo_root, cfg)
    except ValueError as err:
        msg = str(err)
        assert "E_NO_GIT_NO_BUILD_ID" in msg
        assert "set BUILD_ID" in msg
    else:
        raise AssertionError("Expected ValueError for missing git and BUILD_ID")
