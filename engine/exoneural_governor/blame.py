from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ._exec import run_command


def git_available() -> bool:
    proc = run_command("git_version", ["git", "--version"], Path.cwd())
    return proc.returncode == 0


def in_git_repo(repo_root: Path) -> bool:
    proc = run_command("git_inside", ["git", "rev-parse", "--is-inside-work-tree"], repo_root)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _default_ignore_revs_file(repo_root: Path) -> Path | None:
    candidate = repo_root / ".git-blame-ignore-revs"
    return candidate if candidate.exists() else None


def blame_for_path(repo_root: Path, rel_path: str, ignore_revs_file: str | None = None) -> dict[str, Any] | None:
    path = repo_root / rel_path
    if not path.exists() or not path.is_file():
        return None
    cmd = ["git", "blame", "--line-porcelain"]
    ignore = Path(ignore_revs_file) if ignore_revs_file else _default_ignore_revs_file(repo_root)
    if ignore and ignore.exists():
        cmd.extend(["--ignore-revs-file", str(ignore)])
    cmd.extend(["--", rel_path])
    proc = run_command("git_blame", cmd, repo_root)
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
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    top_author, top_lines = ordered[0]
    top_n = [{"author": author, "lines": lines, "share": round(lines / total, 6)} for author, lines in ordered[:5]]
    return {
        "top_author": top_author,
        "top_lines": top_lines,
        "total_lines": total,
        "top_share": round(top_lines / total, 6),
        "authors_topN": top_n,
    }
