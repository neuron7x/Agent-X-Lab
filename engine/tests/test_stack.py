from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.catalog import validate_catalog
from exoneural_governor.config import Config, load_config
from exoneural_governor.release import build_release
from exoneural_governor.vr import run_vr


ENGINE_ROOT = Path(__file__).resolve().parents[1]


def _git_head_available(repo_root: Path) -> bool:
    probe = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def _repo_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "repo-copy"
    shutil.copytree(
        ENGINE_ROOT,
        dst,
        ignore=shutil.ignore_patterns(
            ".git",
            "build_proof",
            "node_modules",
            "artifacts",
            ".pytest*",
            "__pycache__",
        ),
    )
    return dst


def _cfg_for_repo(repo_root: Path) -> Config:
    return Config(
        repo_root=repo_root,
        base_branch="main",
        allowlist_globs=[],
        baseline_commands=[],
        artifact_name="test-release",
        budgets={},
        redaction_policy_path=repo_root / "SECURITY.redaction.yml",
        evidence_root_base=repo_root / "artifacts" / "evidence",
    )


def test_catalog_ok(tmp_path: Path) -> None:
    repo_root = _repo_copy(tmp_path)
    rep = validate_catalog(repo_root)
    assert rep["ok"], rep


def test_vr_and_release(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_copy(tmp_path)
    out_dir = repo_root / "tmp-release-output"
    cfg_path = repo_root / "configs" / "sg.config.json"
    if not _git_head_available(repo_root) and not os.environ.get("BUILD_ID", "").strip():
        monkeypatch.setenv("BUILD_ID", "nogit-test-build-id")

    cfg = load_config(cfg_path)
    vr = run_vr(cfg, write_back=False)
    assert vr["status"] in ("RUN", "CALIBRATION_REQUIRED")

    rel = build_release(cfg, output_dir=out_dir)
    assert (repo_root / rel["zip_path"]).exists()


def test_release_includes_in_repo_evidence_root(tmp_path: Path) -> None:
    repo_root = _repo_copy(tmp_path)
    evidence_dir = repo_root / "tmp-evidence-test"
    out_dir = repo_root / "tmp-release-output"

    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "proof.txt").write_text("ok\n", encoding="utf-8")

    vr_path = tmp_path / "VR.json"
    vr_path.write_text('{"evidence_root": "tmp-evidence-test"}\n', encoding="utf-8")

    rep = build_release(_cfg_for_repo(repo_root), vr_path=vr_path, output_dir=out_dir)

    import zipfile

    zip_path = repo_root / rep["zip_path"]
    with zipfile.ZipFile(zip_path) as zf:
        assert "evidence/proof.txt" in set(zf.namelist())
    assert rep["evidence_included"] is True


def test_release_rejects_out_of_repo_evidence_root(tmp_path: Path) -> None:
    repo_root = _repo_copy(tmp_path)
    out_dir = repo_root / "tmp-release-output"
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    (outside / "secret.txt").write_text("nope\n", encoding="utf-8")

    vr_path = tmp_path / "VR.json"
    vr_path.write_text(
        f'{{"evidence_root": "{outside.as_posix()}"}}\n', encoding="utf-8"
    )

    import pytest

    with pytest.raises(ValueError, match="E_EVIDENCE_ROOT_OUTSIDE_REPO"):
        build_release(_cfg_for_repo(repo_root), vr_path=vr_path, output_dir=out_dir)


def test_release_allows_missing_out_of_repo_evidence_root(tmp_path: Path) -> None:
    repo_root = _repo_copy(tmp_path)
    out_dir = repo_root / "tmp-release-output"
    missing_outside = tmp_path / "missing-outside-evidence"

    vr_path = tmp_path / "VR.json"
    vr_path.write_text(
        f'{{"evidence_root": "{missing_outside.as_posix()}"}}\n',
        encoding="utf-8",
    )

    rep = build_release(_cfg_for_repo(repo_root), vr_path=vr_path, output_dir=out_dir)
    assert rep["evidence_included"] is False


def test_release_sets_evidence_included_false_when_missing_dir(tmp_path: Path) -> None:
    repo_root = _repo_copy(tmp_path)
    out_dir = repo_root / "tmp-release-output"
    vr_path = tmp_path / "VR.json"
    vr_path.write_text(
        '{"evidence_root": "does-not-exist-for-release-test"}\n',
        encoding="utf-8",
    )

    rep = build_release(_cfg_for_repo(repo_root), vr_path=vr_path, output_dir=out_dir)
    assert rep["evidence_included"] is False
