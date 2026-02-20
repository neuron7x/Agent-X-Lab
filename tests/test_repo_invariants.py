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
