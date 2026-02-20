#!/usr/bin/env python3
"""Rebuild catalog/INDEX.json from filesystem.

The index is a lightweight inventory that enables deterministic discovery.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    catalog = repo_root / "catalog"
    if not catalog.exists():
        print("FAIL: missing catalog/")
        return 1

    agents = []
    protocols = []
    stacks = []

    for p in (catalog / "agents").glob("*"):
        if p.is_file():
            agents.append(p.name)
    for p in (catalog / "protocols").glob("*"):
        if p.is_file():
            protocols.append(p.name)
    for p in (catalog / "stacks").rglob("*"):
        if p.is_file():
            stacks.append(p.relative_to(catalog).as_posix())

    idx_path = catalog / "INDEX.json"
    idx: Dict[str, Any] = {}
    if idx_path.exists():
        idx = json.loads(idx_path.read_text(encoding="utf-8"))

    idx["agents"] = sorted(agents)
    idx["protocols"] = sorted(protocols)
    idx["stacks"] = sorted(stacks)

    idx_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print("OK: catalog/INDEX.json rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
