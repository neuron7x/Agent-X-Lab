from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_agent_catalog_has_no_identical_content_duplicates() -> None:
    proc = subprocess.run(
        ["python", "scripts/check_agent_duplicate_content.py", "--repo-root", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
