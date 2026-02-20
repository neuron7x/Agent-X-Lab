from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_protocol_consistency_passes() -> None:
    p = run(
        [
            "python",
            "tools/verify_protocol_consistency.py",
            "--protocol",
            "protocol.yaml",
        ]
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_readme_contract_passes() -> None:
    inv = run(
        [
            "python",
            "tools/titan9_inventory.py",
            "--repo-root",
            ".",
            "--out",
            "artifacts/titan9/inventory.json",
        ]
    )
    assert inv.returncode == 0, inv.stdout + "\n" + inv.stderr

    p = run(
        [
            "python",
            "tools/verify_readme_contract.py",
            "--readme",
            "README.md",
            "--workflows",
            ".github/workflows",
            "--inventory",
            "artifacts/titan9/inventory.json",
        ]
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
