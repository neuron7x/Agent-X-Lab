from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_doctor_passes_in_ci_env() -> None:
    proc = subprocess.run(
        [__import__("sys").executable, "tools/doctor.py", "--quiet"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr


def test_quickstart_script_exists_and_executable() -> None:
    path = REPO_ROOT / "scripts/quickstart.sh"
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("#!")
