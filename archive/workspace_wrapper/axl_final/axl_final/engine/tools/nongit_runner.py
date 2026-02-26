#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DETERMINISTIC_ENV = {
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
    "PYTHONHASHSEED": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
    "GIT_PAGER": "cat",
    "PAGER": "cat",
}


def _copy_repo_without_git(src: Path, dst: Path) -> Path:
    ignore = shutil.ignore_patterns(".git") if (src / ".git").exists() else None
    shutil.copytree(src, dst, ignore=ignore)
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest from a git-free copy of the repository."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root to copy")
    parser.add_argument(
        "--pytest-cmd",
        nargs=argparse.REMAINDER,
        help="Pytest command to run inside the copied repository",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"repo root not found: {repo_root}")

    env = os.environ.copy()
    env["BUILD_ID"] = "test-ci-stub-session"
    env.update(DETERMINISTIC_ENV)

    with tempfile.TemporaryDirectory(prefix="agentx-nongit-") as tempdir:
        copied_repo = Path(tempdir) / repo_root.name
        _copy_repo_without_git(repo_root, copied_repo)

        if (copied_repo / ".git").exists():
            raise RuntimeError("non-git simulation invalid: .git directory exists")

        pytest_cmd = args.pytest_cmd or ["python", "-m", "pytest", "-q", "-W", "error"]
        if pytest_cmd and pytest_cmd[0] == "--":
            pytest_cmd = pytest_cmd[1:]

        proc = subprocess.run(
            pytest_cmd,
            cwd=copied_repo,
            env=env,
            check=False,
        )
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
