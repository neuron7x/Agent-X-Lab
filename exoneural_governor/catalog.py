from __future__ import annotations

import json
from pathlib import Path

from .util import sha256_file, utc_now_iso, write_json


def validate_catalog(repo_root: Path) -> dict:
    idx_path = repo_root / "catalog" / "index.json"
    if not idx_path.exists():
        raise FileNotFoundError(f"Missing catalog index: {idx_path}")

    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    objects = idx.get("objects")
    if not isinstance(objects, list):
        raise ValueError("catalog/index.json must contain objects[]")

    seen_paths: set[str] = set()
    problems: list[dict] = []

    for obj in objects:
        path = obj.get("path")
        sha = obj.get("sha256")
        if not isinstance(path, str) or not isinstance(sha, str):
            problems.append({"type": "bad_entry", "entry": obj})
            continue
        if path in seen_paths:
            problems.append({"type": "duplicate_path", "path": path})
            continue
        seen_paths.add(path)
        abs_path = repo_root / path
        if not abs_path.exists():
            problems.append({"type": "missing_file", "path": path})
            continue
        actual = sha256_file(abs_path)
        if actual != sha:
            problems.append(
                {
                    "type": "sha_mismatch",
                    "path": path,
                    "expected": sha,
                    "actual": actual,
                }
            )

    # Also ensure no unindexed files in catalog/agents+protocols+stacks (fail-closed)
    indexed = {
        o.get("path")
        for o in objects
        if isinstance(o, dict) and isinstance(o.get("path"), str)
    }
    ignore = {(repo_root / "catalog" / "index.json").relative_to(repo_root).as_posix()}
    for p in sorted((repo_root / "catalog").rglob("*")):
        if p.is_file():
            rel = p.relative_to(repo_root).as_posix()
            if rel in ignore:
                continue
            if rel not in indexed and not rel.endswith(".gitkeep"):
                problems.append({"type": "unindexed_file", "path": rel})

    report = {
        "utc": utc_now_iso(),
        "index_path": str(idx_path),
        "ok": len(problems) == 0,
        "problems": problems,
    }
    write_json(repo_root / "artifacts" / "reports" / "catalog.validate.json", report)
    return report
