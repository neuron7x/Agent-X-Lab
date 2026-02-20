#!/usr/bin/env python3
"""Schema-validate the repository's machine-readable artifacts.

Fail-closed:
- If jsonschema is missing => FAIL (CI must install requirements-dev.txt)
- Any validation error => FAIL

Checked artifacts:
- Root MANIFEST.json (schemas/root_manifest.schema.json)
- Each object MANIFEST.json (schemas/object_manifest.schema.json)
- Eval evidence JSON files (schemas/eval_report.schema.json), if present
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


def sha256_hex(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_eval_evidence(repo_root: Path) -> Iterable[Path]:
    for p in repo_root.rglob("evidence/*.json"):
        # avoid large tool caches etc; keep only evidence files
        if p.is_file():
            yield p


def validate_one(validator: Any, instance: Any, schema_name: str, path: Path) -> Tuple[bool, str]:
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, ""
    e = errors[0]
    loc = "/".join(str(x) for x in e.absolute_path) or "(root)"
    return False, f"{schema_name} validation failed for {path}: {loc}: {e.message}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    schemas_dir = repo_root / "schemas"
    if not schemas_dir.exists():
        print("FAIL: missing schemas/ directory")
        return 1

    try:
        import jsonschema  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"FAIL: jsonschema not available: {e!r}")
        return 1

    root_schema = load_json(schemas_dir / "root_manifest.schema.json")
    obj_schema = load_json(schemas_dir / "object_manifest.schema.json")
    eval_schema = load_json(schemas_dir / "eval_report.schema.json")

    root_manifest = load_json(repo_root / "MANIFEST.json")

    Draft = getattr(jsonschema, "Draft202012Validator", jsonschema.Draft7Validator)
    root_validator = Draft(root_schema)
    obj_validator = Draft(obj_schema)
    eval_validator = Draft(eval_schema)

    ok, msg = validate_one(root_validator, root_manifest, "root_manifest", repo_root / "MANIFEST.json")
    if not ok:
        print("FAIL:", msg)
        return 1

    # sanity: checksums format
    for path, meta in (root_manifest.get("checksums") or {}).items():
        if not isinstance(path, str) or not isinstance(meta, dict):
            print(f"FAIL: invalid checksums entry: {path!r} -> {meta!r}")
            return 1
        h = meta.get("sha256")
        if not isinstance(h, str) or not sha256_hex(h):
            print(f"FAIL: invalid checksums sha256: {path!r} -> {h!r}")
            return 1

    # object manifests
    objects = root_manifest.get("objects") or []
    for obj in objects:
        name = (obj or {}).get("name")
        if not name:
            print("FAIL: object entry missing name")
            return 1
        mp = repo_root / "objects" / name / "MANIFEST.json"
        if not mp.exists():
            print(f"FAIL: missing object manifest: {mp}")
            return 1
        inst = load_json(mp)
        ok, msg = validate_one(obj_validator, inst, "object_manifest", mp)
        if not ok:
            print("FAIL:", msg)
            return 1

    # evidence (optional)
    for ev in iter_eval_evidence(repo_root):
        try:
            inst = load_json(ev)
        except Exception as e:
            print(f"FAIL: evidence JSON unreadable: {ev}: {e!r}")
            return 1
        ok, msg = validate_one(eval_validator, inst, "eval_report", ev)
        if not ok:
            print("FAIL:", msg)
            return 1

    print("OK: schemas validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
