from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple, Optional, Set


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj: Dict[str, Any]) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def iter_files(root: str) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            yield os.path.join(dirpath, fn)


def sha256_tree(root: str, *, exclude_rel_paths: Optional[Set[str]] = None, exclude_rel_prefixes: Optional[Set[str]] = None) -> Tuple[str, Dict[str, str]]:
    """
    Deterministic directory hashing:
    - hashes each file
    - hashes the sorted mapping of relative paths -> file hash
    Returns: (tree_hash, file_hashes)
    """
    file_hashes: Dict[str, str] = {}
    root = os.path.abspath(root)
    exclude_rel_paths = set(exclude_rel_paths or set())
    exclude_rel_prefixes = set(exclude_rel_prefixes or set())
    for path in iter_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        if rel in exclude_rel_paths or any(rel.startswith(prefix) for prefix in exclude_rel_prefixes):
            continue
        file_hashes[rel] = sha256_file(path)

    tree_hash = sha256_json(file_hashes)
    return tree_hash, file_hashes
