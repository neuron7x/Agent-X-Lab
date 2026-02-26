#!/usr/bin/env python3
"""Fail if catalog/agents contains files with identical byte content."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    agent_dir = repo_root / "catalog" / "agents"
    if not agent_dir.exists():
        print("FAIL: missing catalog/agents")
        return 1

    by_hash: dict[str, list[str]] = {}
    for path in sorted(agent_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        by_hash.setdefault(sha256_file(path), []).append(rel)

    duplicates = [group for group in by_hash.values() if len(group) > 1]
    duplicates.sort(key=lambda group: tuple(group))
    if duplicates:
        print("FAIL: duplicate agent definitions detected")
        for group in duplicates:
            print(" - " + ", ".join(group))
        return 1

    print("OK: no duplicate-content agent definitions found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
