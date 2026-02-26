from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .anchors import sha256_tree, sha256_file


@dataclass(frozen=True)
class ComponentRef:
    name: str
    path: str
    kind: str  # "ui" | "engine" | "sdk" | "legacy" | "docs"
    hash: str


@dataclass(frozen=True)
class UDGSSystemObject:
    """
    Single integrated system object:
    - references UI/Engine/SDKs
    - holds deterministic hashes as audit anchors
    - is config-driven
    """
    config: Dict[str, Any]
    components: Dict[str, ComponentRef]
    system_anchor: str


def build_system_object(root: str, config_path: str) -> UDGSSystemObject:
    root = os.path.abspath(root)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    comps: Dict[str, ComponentRef] = {}

    def add_tree(name: str, rel_path: str, kind: str, *, exclude_rel_paths: Optional[set[str]] = None, exclude_rel_prefixes: Optional[set[str]] = None) -> None:
        abs_path = os.path.join(root, rel_path)
        tree_hash, _ = sha256_tree(abs_path, exclude_rel_paths=exclude_rel_paths, exclude_rel_prefixes=exclude_rel_prefixes)
        comps[name] = ComponentRef(name=name, path=rel_path, kind=kind, hash=tree_hash)

    audit_excludes = set(config.get("audit_exclude_rel_paths", []))
    audit_exclude_prefixes = set(config.get("audit_exclude_rel_prefixes", []))

    # Contracted layout (defaults)
    add_tree("AXL_UI", ".", "ui", exclude_rel_paths=audit_excludes, exclude_rel_prefixes=audit_exclude_prefixes)
    if os.path.isdir(os.path.join(root, "engine")):
        add_tree("AXL_ENGINE", "engine", "engine")
    if os.path.isdir(os.path.join(root, "tools/dao-arbiter")):
        add_tree("DAO_ARBITER_SDK", "tools/dao-arbiter", "sdk")
    if os.path.isdir(os.path.join(root, "sources/legacy/E-legacy_snapshot")):
        add_tree("E_LEGACY_SDK", "sources/legacy/E-legacy_snapshot", "legacy")
    # (tools/E-legacy is deprecated; kept only as snapshot)
        # deprecated: tools/E-legacy
    if os.path.isdir(os.path.join(root, "system")):
        add_tree("SYSTEM_DOCS", "system", "docs")

    # System anchor: hash over component hashes + config hash
    config_hash = sha256_file(config_path)
    anchor_payload = {"config_hash": config_hash, "components": {k: v.hash for k, v in sorted(comps.items())}}
    system_anchor = sha256_tree_payload(anchor_payload)

    return UDGSSystemObject(config=config, components=comps, system_anchor=system_anchor)


def sha256_tree_payload(payload: Dict[str, Any]) -> str:
    import hashlib
    b = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def write_system_object(path: str, obj: UDGSSystemObject) -> None:
    data = {
        "config": obj.config,
        "components": {k: {"name": v.name, "path": v.path, "kind": v.kind, "hash": v.hash} for k, v in obj.components.items()},
        "system_anchor": obj.system_anchor,
        "audit": {
            "excluded_from_root_hash": list(obj.config.get("audit_exclude_rel_paths", [])),
            "excluded_prefixes_from_root_hash": list(obj.config.get("audit_exclude_rel_prefixes", []))
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
