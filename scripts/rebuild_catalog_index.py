#!/usr/bin/env python3
"""Rebuild catalog/index.json from filesystem."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import hashlib
from datetime import datetime, timezone


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def existing_generated_utc(index_path: Path) -> str | None:
    if not index_path.exists():
        return None
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("generated_utc")
    return value if isinstance(value, str) else None


def _kind(rel: str) -> str:
    if rel.startswith("catalog/agents/"):
        return "agent"
    if rel.startswith("catalog/protocols/"):
        return "protocol"
    if rel.startswith("catalog/stacks/"):
        return "stack"
    return "catalog"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    catalog = repo_root / "catalog"
    if not catalog.exists():
        print("FAIL: missing catalog/")
        return 1

    objects = []
    agents = []
    protocols = []
    stacks = []

    for p in sorted(catalog.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root).as_posix()
        if rel in {"catalog/index.json", "catalog/INDEX.json"}:
            continue
        name = p.stem
        k = _kind(rel)
        if k == "agent":
            agents.append(p.name)
        elif k == "protocol":
            protocols.append(p.name)
        elif k == "stack":
            stacks.append(p.relative_to(catalog).as_posix())
        objects.append({"name": name, "path": rel, "sha256": sha256_file(p), "type": k})

    idx_path = catalog / "index.json"
    generated_utc = existing_generated_utc(idx_path) or utc_now_iso()

    idx: Dict[str, Any] = {
        "catalog_id": "AGENTX-LAB",
        "version": "0.1.0",
        "generated_utc": generated_utc,
        "count": len(objects),
        "objects": objects,
        "agents": sorted(agents),
        "protocols": sorted(protocols),
        "stacks": sorted(stacks),
    }

    idx_path.write_text(
        json.dumps(idx, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print("OK: catalog/index.json rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
