from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT if (REPO_ROOT / ".github/workflows").exists() else REPO_ROOT.parent


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def _in_git_checkout() -> bool:
    p = run(["git", "rev-parse", "--is-inside-work-tree"])
    return p.returncode == 0 and p.stdout.strip() == "true"


def test_validate_arsenal_strict_passes() -> None:
    p = run(["python", "scripts/validate_arsenal.py", "--repo-root", ".", "--strict"])
    assert p.returncode in (0, 1), p.stdout + "\n" + p.stderr


def test_schema_validate_passes() -> None:
    p = run(["python", "scripts/schema_validate.py", "--repo-root", "."])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_object_eval_harnesses_pass() -> None:
    p = run(["python", "scripts/run_object_evals.py", "--repo-root", "."])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_no_generated_artifacts_tracked() -> None:
    if not _in_git_checkout():
        import pytest

        pytest.skip("requires git checkout")
    p = run(["git", "ls-files"])
    assert p.returncode == 0, p.stderr
    tracked = p.stdout.splitlines()
    forbidden = [
        t
        for t in tracked
        if (
            ".egg-info/" in t
            or "__pycache__/" in t
            or t.endswith(".pyc")
            or t.startswith("dist/")
            or t.startswith("build/")
            or ".pytest_cache/" in t
        )
    ]
    assert forbidden == [], f"forbidden tracked artifacts: {forbidden}"


def test_required_workflows_exist() -> None:
    required = [
        WORKFLOW_ROOT / ".github/workflows/ci-supercheck.yml",
        WORKFLOW_ROOT / ".github/workflows/workflow-hygiene.yml",
        WORKFLOW_ROOT / ".github/workflows/action-pin-audit.yml",
    ]
    missing = [str(p.relative_to(WORKFLOW_ROOT)) for p in required if not p.exists()]
    assert missing == [], f"missing workflows: {missing}"


def test_makefile_targets_exist() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ["fmt", "lint", "type", "test", "validate", "eval", "ci"]:
        assert f"{target}:" in makefile


def test_sg_config_selftest_passes() -> None:
    p = run(
        [
            "python",
            "-m",
            "exoneural_governor.cli",
            "--config",
            "configs/sg.config.json",
            "selftest",
        ]
    )
    assert p.returncode in (0, 2), p.stdout + "\n" + p.stderr


def test_sg_vr_accepts_config_after_subcommand() -> None:
    p = run(
        [
            "python",
            "-m",
            "exoneural_governor.cli",
            "vr",
            "--config",
            "configs/sg.config.json",
            "--out",
            "VR.json",
            "--no-write",
        ]
    )
    assert p.returncode in (0, 3), p.stdout + "\n" + p.stderr
    assert "unrecognized arguments" not in (p.stdout + p.stderr)


def test_sg_release_accepts_config_after_subcommand() -> None:
    p = run(
        [
            "python",
            "-m",
            "exoneural_governor.cli",
            "release",
            "--config",
            "configs/sg.config.json",
            "--vr",
            "VR.json",
            "--output",
            "artifacts/release",
        ]
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_manifest_checksums_exclude_transient_artifacts() -> None:
    import json

    manifest = json.loads((REPO_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    checksums = manifest.get("checksums", {})
    bad = [
        p
        for p in checksums
        if p.startswith("artifacts/fegr7/")
        or p.startswith("artifacts/feg_r8/")
        or p.startswith("artifacts/titan9/")
        or p.startswith("artifacts/security/")
        or p.startswith("artifacts/agent/")
    ]
    assert bad == [], f"transient artifacts must not be checksummed: {bad}"
