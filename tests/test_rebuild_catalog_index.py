from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_rebuild() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/rebuild_catalog_index.py",
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_rebuild_catalog_index_preserves_generated_utc() -> None:
    index_path = REPO_ROOT / "catalog/index.json"
    original = json.loads(index_path.read_text(encoding="utf-8"))
    original_generated_utc = original["generated_utc"]

    first = run_rebuild()
    assert first.returncode == 0, first.stdout + "\n" + first.stderr

    second = run_rebuild()
    assert second.returncode == 0, second.stdout + "\n" + second.stderr

    rebuilt = json.loads(index_path.read_text(encoding="utf-8"))
    assert rebuilt["generated_utc"] == original_generated_utc
