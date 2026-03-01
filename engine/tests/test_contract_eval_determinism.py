from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_contract_eval_canonical_digests_present(tmp_path: Path) -> None:
    repo_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip())
    proc = subprocess.run(
            [
                "python",
                "-m",
                "exoneural_governor",
                "contract-eval",
                "--out",
                str(tmp_path),
                "--strict-no-write",
                "--json",
            ],
            cwd=repo_root / "engine",
            capture_output=True,
            text=True,
            check=False,
        )
    assert proc.returncode in (0, 2)
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    gate = next(g for g in report["gates"] if g["id"] == "GATE_A06_DETERMINISM_SIGNATURE")
    assert "signature_run1_sha256" in gate["details"]
    assert "signature_run2_sha256" in gate["details"]
    assert (tmp_path / "signature.run1.json").exists()
    assert (tmp_path / "signature.run2.json").exists()
