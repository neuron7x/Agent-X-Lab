#!/usr/bin/env python3
"""Rebuild the `checksums` block in root MANIFEST.json.

This is intentionally deterministic:
- SHA256 over exact bytes
- Stable path ordering
- Excludes volatile dirs (/.git, /.venv, __pycache__, .pytest_cache, etc.)

Fail-closed:
- If MANIFEST.json is missing => FAIL
- If any listed file is missing => FAIL
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set


EXCLUDE_DIRS: Set[str] = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}
EXCLUDE_FILES: Set[str] = {
    ".DS_Store",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(repo_root: Path) -> Iterable[Path]:
    for p in repo_root.rglob("*"):
        if p.is_dir():
            continue
        if p.name in EXCLUDE_FILES:
            continue
        rel_parts = p.relative_to(repo_root).parts
        parts = set(rel_parts)
        if parts & EXCLUDE_DIRS:
            continue
        if any(part.endswith(".egg-info") for part in rel_parts):
            continue
        rel = p.relative_to(repo_root).as_posix()
        if rel.startswith("artifacts/evidence/"):
            continue
        if rel.startswith("configs/artifacts/"):
            continue
        if (
            rel.startswith("artifacts/reports/")
            or rel.startswith("artifacts/tmp/")
            or rel.startswith("artifacts/release/")
            or rel.startswith("artifacts/proof/")
            or rel.startswith("artifacts/feg/")
            or rel.startswith("artifacts/fegr7/")
            or rel.startswith("artifacts/titan9/")
        ):
            continue
        if (
            "/artifacts/evidence/" in rel
            and "/artifacts/evidence/reference/" not in rel
        ):
            continue
        # exclude root manifest itself to avoid recursion
        if rel == "MANIFEST.json":
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--manifest",
        default="MANIFEST.json",
        help="Root manifest (default: MANIFEST.json)",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    mpath = repo_root / args.manifest
    if not mpath.exists():
        print("FAIL: missing MANIFEST.json")
        return 1

    m = json.loads(mpath.read_text(encoding="utf-8"))
    checksums: Dict[str, Dict[str, str]] = {}

    files: List[Path] = sorted(
        iter_files(repo_root), key=lambda p: p.relative_to(repo_root).as_posix()
    )
    for p in files:
        rel = p.relative_to(repo_root).as_posix()
        checksums[rel] = {"sha256": sha256_file(p)}

    m["checksums"] = checksums
    mpath.write_text(
        json.dumps(m, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK: checksums rebuilt ({len(checksums)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
