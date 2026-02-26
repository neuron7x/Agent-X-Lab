#!/usr/bin/env python3
"""Repository verification script (truth-plane local replica).

Checks:
1) JSON examples validate against their JSON Schemas.
2) PROOF_BUNDLE.example.json artifact_hashes match current file SHA-256.

Exit code 0 on pass, non-zero on failure.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    import jsonschema
except Exception as e:  # pragma: no cover
    print("ERROR: missing dependency 'jsonschema'. Install with: pip install jsonschema", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    fail_schema = load_json(ROOT / "FAIL_PACKET.json")
    proof_schema = load_json(ROOT / "PROOF_BUNDLE.json")

    fail_ex = load_json(ROOT / "examples" / "FAIL_PACKET.example.json")
    proof_ex = load_json(ROOT / "examples" / "PROOF_BUNDLE.example.json")

    # 1) Schema validation
    jsonschema.validate(instance=fail_ex, schema=fail_schema)
    jsonschema.validate(instance=proof_ex, schema=proof_schema)

    # 2) Hash validation
    ah = proof_ex.get("artifact_hashes", {})
    errors = 0
    for rel, expected in ah.items():
        p = ROOT / rel
        if not p.exists():
            print(f"ERROR: artifact missing: {rel}", file=sys.stderr)
            errors += 1
            continue
        got = sha256_file(p)
        if got.lower() != expected.lower():
            print(f"ERROR: hash mismatch for {rel}", file=sys.stderr)
            print(f"  expected: {expected}", file=sys.stderr)
            print(f"  got:      {got}", file=sys.stderr)
            errors += 1
    if errors:
        return 2

    print("OK: schemas valid; proof bundle artifact hashes match.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
