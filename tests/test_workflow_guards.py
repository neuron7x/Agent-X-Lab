from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_verify_workflow_hygiene_passes() -> None:
    p = _run(["python", "tools/verify_workflow_hygiene.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_verify_action_pinning_passes() -> None:
    p = _run(["python", "tools/verify_action_pinning.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
