#!/usr/bin/env python3
"""
AgentX Lab CLI

This is a thin wrapper over:
  - scripts/validate_arsenal.py
  - scripts/run_object_evals.py

Fail-closed: propagates non-zero exits.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(prog="arsenal")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate repository structure + checksums")
    p_val.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    p_val.add_argument(
        "--strict", action="store_true", help="Strict mode (recommended)"
    )

    p_eval = sub.add_parser("eval", help="Run eval harnesses for all objects")
    p_eval.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    p_eval.add_argument(
        "--write-evidence",
        action="store_true",
        help="Write evidence under objects/*/artifacts/evidence/",
    )
    p_eval.add_argument(
        "--deterministic",
        action="store_true",
        help="Deterministic run (writes to reference/)",
    )

    p_schema = sub.add_parser(
        "schema", help="Validate JSON artifacts against JSON Schemas"
    )
    p_schema.add_argument("--repo-root", default=".", help="Repo root (default: .)")

    p_rebuild = sub.add_parser(
        "rebuild", help="Rebuild checksums and catalog index deterministically"
    )
    p_rebuild.add_argument("--repo-root", default=".", help="Repo root (default: .)")

    p_pack = sub.add_parser(
        "package", help="Create a clean release zip (no runtime evidence)"
    )
    p_pack.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    p_pack.add_argument("--out", default="agentx-lab.zip", help="Output zip path")

    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    if args.cmd == "validate":
        cmd = ["python", "scripts/validate_arsenal.py", "--repo-root", str(root)]
        if args.strict:
            cmd.append("--strict")
        return subprocess.run(cmd).returncode

    if args.cmd == "eval":
        cmd = ["python", "scripts/run_object_evals.py", "--repo-root", str(root)]
        if args.deterministic:
            cmd.append("--deterministic")
        if args.write_evidence:
            cmd.append("--write-evidence")
        return subprocess.run(cmd).returncode

    if args.cmd == "schema":
        cmd = ["python", "scripts/schema_validate.py", "--repo-root", str(root)]
        return subprocess.run(cmd).returncode

    if args.cmd == "rebuild":
        rc = subprocess.run(
            ["python", "scripts/rebuild_checksums.py", "--repo-root", str(root)]
        ).returncode
        if rc != 0:
            return rc
        return subprocess.run(
            ["python", "scripts/rebuild_catalog_index.py", "--repo-root", str(root)]
        ).returncode

    if args.cmd == "package":
        import zipfile

        out = Path(args.out).resolve()
        # Package the repo root directory, excluding runtime evidence (keep reference).
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_dir():
                    continue
                rel = p.relative_to(root).as_posix()
                if rel.startswith(".git/"):
                    continue
                if rel.startswith("objects/") and "/artifacts/evidence/" in rel:
                    if "/artifacts/evidence/reference/" not in rel and not rel.endswith(
                        "artifacts/evidence/.gitkeep"
                    ):
                        continue
                z.write(p, arcname=f"agentx-lab/{rel}")
        print(str(out))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
