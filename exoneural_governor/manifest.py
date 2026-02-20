from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .util import sha256_file, utc_now_iso, write_json


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str
    size_bytes: int


def build_manifest(root: Path, *, include_globs: Iterable[str] | None = None) -> dict:
    """Create a sha256 manifest for all files under root (deterministic order)."""
    entries: list[ManifestEntry] = []
    for p in sorted([x for x in root.rglob("*") if x.is_file()], key=lambda x: x.as_posix()):
        rel = p.relative_to(root).as_posix()
        entries.append(ManifestEntry(path=rel, sha256=sha256_file(p), size_bytes=p.stat().st_size))

    obj = {
        "utc": utc_now_iso(),
        "root": str(root),
        "entries": [e.__dict__ for e in entries],
        "count": len(entries),
    }
    return obj


def write_manifest(root: Path, out_path: Path) -> dict:
    man = build_manifest(root)
    write_json(out_path, man)
    return man
