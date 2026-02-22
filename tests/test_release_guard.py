from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_release_guard_pr_mode_passes() -> None:
    p = _run(["python", "tools/release_guard.py", "--mode", "pr"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_release_guard_release_mode_passes_current_version() -> None:
    p = _run(["python", "tools/release_guard.py", "--mode", "release", "--version", "0.1.0"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
