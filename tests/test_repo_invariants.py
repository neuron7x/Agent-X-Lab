from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_validate_arsenal_strict_passes() -> None:
    p = run(["python", "scripts/validate_arsenal.py", "--repo-root", ".", "--strict"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_schema_validate_passes() -> None:
    p = run(["python", "scripts/schema_validate.py", "--repo-root", "."])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_object_eval_harnesses_pass() -> None:
    p = run(["python", "scripts/run_object_evals.py", "--repo-root", "."])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_no_generated_artifacts_tracked() -> None:
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
        REPO_ROOT / ".github/workflows/ci.yml",
        REPO_ROOT / ".github/workflows/security.yml",
        REPO_ROOT / ".github/workflows/lint-actions.yml",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.exists()]
    assert missing == [], f"missing workflows: {missing}"


def test_makefile_targets_exist() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ["setup", "fmt", "lint", "type", "test", "validate", "eval", "proof", "ci"]:
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
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


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
