from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .util import redact_bytes


def load_redaction_patterns(path: Path) -> list[str]:
    if not path.exists():
        # Fail-closed: redaction policy is mandatory for evidence.
        raise FileNotFoundError(f"Missing redaction policy: {path}")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("SECURITY.redaction.yml must be a mapping")
    pats = doc.get("patterns")
    if not isinstance(pats, list) or not all(isinstance(x, str) for x in pats):
        raise ValueError("SECURITY.redaction.yml must contain patterns: [regex...]")
    return list(pats)


def redact_file_inplace(path: Path, patterns: Iterable[str]) -> None:
    path.write_bytes(redact_bytes(path.read_bytes(), patterns))


def redact_tree(
    root: Path, patterns: Iterable[str], *, include_exts: set[str] | None = None
) -> list[str]:
    changed: list[str] = []
    include_exts = include_exts or {
        ".txt",
        ".log",
        ".out",
        ".err",
        ".json",
        ".md",
        ".yml",
        ".yaml",
    }
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in include_exts:
            before = p.read_bytes()
            after = redact_bytes(before, patterns)
            if after != before:
                p.write_bytes(after)
                changed.append(str(p))
    return changed
