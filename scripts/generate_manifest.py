#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = ROOT / "artifacts" / "proof_bundle"
MANIFEST_PATH = PROOF_DIR / "MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = []
    for path in sorted(PROOF_DIR.rglob("*")):
        if not path.is_file() or path == MANIFEST_PATH:
            continue
        rel = path.relative_to(ROOT).as_posix()
        files.append({"path": rel, "sha256": sha256(path)})
    payload = {"files": files}
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
