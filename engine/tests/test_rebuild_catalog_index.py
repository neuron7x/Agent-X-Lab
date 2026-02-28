from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]


def run_rebuild(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/rebuild_catalog_index.py",
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_rebuild_catalog_index_preserves_generated_utc(tmp_path: Path) -> None:
    repo_copy = tmp_path / "engine-copy"
    shutil.copytree(ENGINE_ROOT, repo_copy)

    index_path = repo_copy / "catalog/index.json"
    original = json.loads(index_path.read_text(encoding="utf-8"))
    original_generated_utc = original["generated_utc"]

    first = run_rebuild(repo_copy)
    assert first.returncode == 0, first.stdout + "\n" + first.stderr

    second = run_rebuild(repo_copy)
    assert second.returncode == 0, second.stdout + "\n" + second.stderr

    rebuilt = json.loads(index_path.read_text(encoding="utf-8"))
    assert rebuilt["generated_utc"] == original_generated_utc
