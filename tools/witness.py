#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, shell=False, capture_output=True, text=True)
    output = (p.stdout or "") + (p.stderr or "")
    tail = "\n".join(output.splitlines()[-20:])
    return {
        "cmd": shlex.join(cmd),
        "exit": p.returncode,
        "tail_sha256": hashlib.sha256(tail.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    out_dir = Path("artifacts/feg_r8/attestation")
    out_dir.mkdir(parents=True, exist_ok=True)

    replay = [
        _run(["python", "tools/verify_workflow_hygiene.py"]),
        _run(["python", "tools/verify_action_pinning.py"]),
    ]

    watched = [
        Path("artifacts/feg_r8/gates.jsonl"),
        Path("artifacts/feg_r8/minimality/report.json"),
        Path("artifacts/feg_r8/minimality/trace.jsonl"),
    ]
    hashes = {p.as_posix(): _sha256_file(p) for p in watched if p.exists()}

    canonical = json.dumps({"hashes": hashes, "replay": replay}, sort_keys=True)
    key = os.environ.get("FEG_WITNESS_KEY", "")
    unsigned = key == ""
    if unsigned:
        signature = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    else:
        signature = hmac.new(
            key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha512
        ).hexdigest()

    report = {
        "unsigned_witness": unsigned,
        "replay": replay,
        "hashes": hashes,
        "signature_algorithm": "sha256" if unsigned else "hmac-sha512",
        "signature": signature,
        "pass": all(int(r.get("exit", 1)) == 0 for r in replay),
    }

    (out_dir / "witness_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "witness_sig.txt").write_text(signature + "\n", encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
