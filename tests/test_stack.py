from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.catalog import validate_catalog
from exoneural_governor.config import Config, load_config
from exoneural_governor.vr import run_vr
from exoneural_governor.release import build_release


def _git_head_available(repo_root: Path) -> bool:
    probe = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def test_catalog_ok():
    repo_root = Path(__file__).resolve().parents[1]
    rep = validate_catalog(repo_root)
    assert rep["ok"], rep


def test_vr_and_release(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    if (
        not _git_head_available(repo_root)
        and not os.environ.get("BUILD_ID", "").strip()
    ):
        monkeypatch.setenv("BUILD_ID", "nogit-test-build-id")
    cfg = load_config(repo_root / "configs" / "sg.config.json")
    vr = run_vr(cfg, write_back=False)
    assert vr["status"] in ("RUN", "CALIBRATION_REQUIRED")
    rel = build_release(cfg)
    assert (repo_root / rel["zip_path"]).exists()


def test_release_includes_in_repo_evidence_root(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    evidence_dir = repo_root / "artifacts" / "tmp-evidence-test"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "proof.txt"
    evidence_file.write_text("ok\n", encoding="utf-8")

    vr_path = tmp_path / "VR.json"
    vr_path.write_text(
        '{"evidence_root": "artifacts/tmp-evidence-test"}\n', encoding="utf-8"
    )

    cfg = Config(
        repo_root=repo_root,
        base_branch="main",
        allowlist_globs=[],
        baseline_commands=[],
        artifact_name="test-release",
        budgets={},
        redaction_policy_path=repo_root / "SECURITY.redaction.yml",
        evidence_root_base=repo_root / "artifacts" / "evidence",
    )

    out_dir = repo_root / "artifacts" / "release-test"
    rep = build_release(cfg, vr_path=vr_path, output_dir=out_dir)
    import zipfile

    zip_path = repo_root / rep["zip_path"]
    with zipfile.ZipFile(zip_path) as z:
        assert "evidence/proof.txt" in set(z.namelist())


def test_release_rejects_out_of_repo_evidence_root(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    (outside / "secret.txt").write_text("nope\n", encoding="utf-8")

    vr_path = tmp_path / "VR.json"
    vr_path.write_text(
        f'{{"evidence_root": "{outside.as_posix()}"}}\n', encoding="utf-8"
    )

    cfg = Config(
        repo_root=repo_root,
        base_branch="main",
        allowlist_globs=[],
        baseline_commands=[],
        artifact_name="test-release",
        budgets={},
        redaction_policy_path=repo_root / "SECURITY.redaction.yml",
        evidence_root_base=repo_root / "artifacts" / "evidence",
    )

    import pytest

    with pytest.raises(ValueError, match="E_EVIDENCE_ROOT_OUTSIDE_REPO"):
        build_release(
            cfg, vr_path=vr_path, output_dir=repo_root / "artifacts" / "release-test"
        )
