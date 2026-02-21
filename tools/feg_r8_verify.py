#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path


def run(cmd: str) -> dict[str, object]:
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    output = (p.stdout or "") + (p.stderr or "")
    tail = "\n".join(output.splitlines()[-20:])
    return {
        "cmd": cmd,
        "exit": p.returncode,
        "duration_s": round(time.time() - t0, 3),
        "log_tail_sha256": hashlib.sha256(tail.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    outdir = Path("artifacts/feg_r8")
    outdir.mkdir(parents=True, exist_ok=True)
    gates = [
        "python tools/verify_workflow_hygiene.py",
        "python tools/verify_action_pinning.py",
        "python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json",
    ]
    results = [run(cmd) for cmd in gates]
    (outdir / "gates.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in results) + "\n",
        encoding="utf-8",
    )
    failed = [r for r in results if r["exit"] != 0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
