from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools import nongit_runner


def test_copy_repo_without_git_excludes_dot_git(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (src / "module.py").write_text("print('ok')\n", encoding="utf-8")

    dst = tmp_path / "dst"
    nongit_runner._copy_repo_without_git(src, dst)

    assert (dst / "module.py").exists()
    assert not (dst / ".git").exists()


def test_nongit_runner_executes_pytest_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "tests").mkdir()
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 == 1\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "tools/nongit_runner.py",
            "--repo-root",
            str(repo),
            "--pytest-cmd",
            sys.executable,
            "-m",
            "pytest",
            "-q",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
