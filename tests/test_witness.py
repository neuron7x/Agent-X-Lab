from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_witness_writes_report_and_signature() -> None:
    base = REPO_ROOT / "artifacts" / "feg_r8"
    (base / "minimality").mkdir(parents=True, exist_ok=True)
    (base / "gates.jsonl").write_text('{"cmd":"x","exit":0}\n', encoding="utf-8")
    (base / "minimality" / "report.json").write_text(
        '{"minimality_pass":true}\n', encoding="utf-8"
    )
    (base / "minimality" / "trace.jsonl").write_text('{"trial":1}\n', encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "tools/witness.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    report = json.loads(
        (base / "attestation" / "witness_report.json").read_text(encoding="utf-8")
    )
    sig = (base / "attestation" / "witness_sig.txt").read_text(encoding="utf-8").strip()
    assert report["signature"] == sig
