from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def git_available() -> bool:
    proc = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
    return proc.returncode == 0


def in_git_repo(repo_root: Path) -> bool:
    proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root, capture_output=True, text=True, check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def blame_for_path(repo_root: Path, rel_path: str) -> dict[str, Any] | None:
    path = repo_root / rel_path
    if not path.exists() or not path.is_file():
        return None
    proc = subprocess.run(
        ["git", "blame", "--line-porcelain", "--", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    counts: Counter[str] = Counter()
    current_author = None
    for line in proc.stdout.splitlines():
        if line.startswith("author-mail "):
            current_author = line[len("author-mail ") :].strip().strip("<>")
        elif line.startswith("\t"):
            if current_author:
                counts[current_author] += 1
            current_author = None
    total = sum(counts.values())
    if total <= 0:
        return None
    top_author, top_lines = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
    return {
        "top_author": top_author,
        "top_lines": top_lines,
        "total_lines": total,
        "top_share": round(top_lines / total, 6),
    }
