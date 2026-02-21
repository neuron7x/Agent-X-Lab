from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


from tools.verify_readme_contract import E_README_QUICKSTART_MAKE_ONLY

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


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


def test_readme_contract_fails_when_quickstart_not_make_only_stable() -> None:
    expected = E_README_QUICKSTART_MAKE_ONLY
    outputs: list[str] = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        readme = temp_path / "README.md"
        workflows = temp_path / "workflows"
        workflows.mkdir(parents=True, exist_ok=True)
        (workflows / "ci.yml").write_text(
            """
name: CI
jobs:
  quality:
    runs-on: ubuntu-latest
    env:
      PYTHONHASHSEED: "0"
    steps:
      - name: Example
        run: make check
""".strip()
            + "\n",
            encoding="utf-8",
        )

        inventory = temp_path / "inventory.json"
        inventory.write_text(
            json.dumps({"canonical_commands": {"tests": ["make check"]}}) + "\n",
            encoding="utf-8",
        )

        readme.write_text(
            """
## Quickstart

```bash
python -m pytest -q -W error
```
""".strip()
            + "\n",
            encoding="utf-8",
        )

        for _ in range(3):
            proc = run(
                [
                    "python",
                    str(REPO_ROOT / "tools/verify_readme_contract.py"),
                    "--readme",
                    str(readme),
                    "--workflows",
                    str(workflows),
                    "--inventory",
                    str(inventory),
                ],
                cwd=temp_path,
            )
            assert proc.returncode != 0
            outputs.append(proc.stderr.strip())

    assert outputs == [expected, expected, expected]


def test_generate_titan9_proof_bundle() -> None:
    p = run(["python", "tools/generate_titan9_proof.py", "--repo-root", "."])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

    for rel in [
        "artifacts/titan9/inventory.json",
        "artifacts/titan9/readme_commands.json",
        "artifacts/titan9/proof.log",
        "artifacts/titan9/hashes.json",
    ]:
        assert (REPO_ROOT / rel).exists(), rel
