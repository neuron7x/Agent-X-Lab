#!/usr/bin/env python3
"""Create deterministic artifacts/AC.package (ZIP, stored, stable order+timestamps).

AC.package is treated as the sealed, canonical release payload for PROD_SPEC.

Rules (conservative):
- Include: source + built frontend dist/ + worker + engine + udgs_core + system + docs.
- Exclude: caches, CI local outputs, previous proof/build artifacts that would self-reference.

The output is deterministic given identical input file bytes.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
import zipfile

FIXED_ZIP_DT = (1980, 1, 1, 0, 0, 0)

DEFAULT_INCLUDE = [
    "README.md",
    "UNIFIED_SYSTEM.md",
    "SYSTEM_OBJECT.json",
    "UDGS_MANIFEST.json",
    "RELEASES_MANIFEST.json",
    "engine/**",
    "udgs_core/**",
    "system/**",
    "docs/**",
    "src/**",
    "public/**",
    "index.html",
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "postcss.config.js",
    "tailwind.config.ts",
    "eslint.config.js",
    "components.json",
    "vercel.json",
    ".nvmrc",
    ".env.example",
    "workers/**",
    "tools/dao-arbiter/**",
    "sources/**",
    "releases/**",
    "dist/**",
]

DEFAULT_EXCLUDE_GLOBS = [
    ".git/**",
    "**/.DS_Store",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/.pytest_cache/**",
    "**/.hypothesis/**",
    "**/node_modules/**",
    "build_proof/**",
    "qa8_state/**",
    "artifacts/AC.package",
    "artifacts/rebuilt_artifact",
    "artifacts/*.sha256",
    "artifacts/build.lock",
    "artifacts/build.provenance",
    "artifacts/rebuild.log",
    "artifacts/replay.report",
    "artifacts/env.fingerprint",
    "artifacts/model_check.report",
    "artifacts/SMT.bridge",
    "artifacts/SPS.candidates",
    "artifacts/verifier.rules",
    "artifacts/selection.proof",
    "artifacts/AC.signature.jws",
    "artifacts/AC.root_key.pub",
    "artifacts/gate_check.report.json",
]


def _matches_any(path_posix: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path_posix, g) for g in globs)


def iter_files(root: Path, includes: list[str], excludes: list[str]) -> list[Path]:
    out: list[Path] = []

    # Expand include patterns
    for pat in includes:
        # Handle literal file
        if "*" not in pat and "?" not in pat and "[" not in pat and "**" not in pat:
            p = root / pat
            if p.exists() and p.is_file():
                out.append(p)
            elif p.exists() and p.is_dir():
                out.extend([x for x in p.rglob("*") if x.is_file()])
            continue

        # Glob patterns
        if "**" in pat:
            base = pat.split("**")[0].rstrip("/")
            base_dir = root / base
            if not base_dir.exists():
                continue
            for f in base_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(root).as_posix()
                    if fnmatch.fnmatch(rel, pat.replace("**", "*")) or rel.startswith(base + "/"):
                        out.append(f)
        else:
            for f in root.glob(pat):
                if f.is_file():
                    out.append(f)
                elif f.is_dir():
                    out.extend([x for x in f.rglob("*") if x.is_file()])

    # Dedup, apply exclude filters, sort
    unique: dict[str, Path] = {}
    for f in out:
        rel = f.relative_to(root).as_posix()
        if _matches_any(rel, excludes):
            continue
        unique[rel] = f

    return [unique[k] for k in sorted(unique.keys())]


def write_zip(root: Path, out_path: Path, includes: list[str], excludes: list[str]) -> tuple[int, int]:
    files = iter_files(root, includes, excludes)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_STORED) as z:
        for f in files:
            rel = f.relative_to(root).as_posix()
            data = f.read_bytes()
            zi = zipfile.ZipInfo(rel)
            zi.date_time = FIXED_ZIP_DT
            zi.compress_type = zipfile.ZIP_STORED
            # stable UNIX perms: 0644
            zi.external_attr = (0o100644 & 0xFFFF) << 16
            z.writestr(zi, data)

    return len(files), out_path.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root")
    ap.add_argument("--out", default="artifacts/AC.package", help="Output path")
    ap.add_argument("--include", action="append", default=[], help="Include glob (repeatable)")
    ap.add_argument("--exclude", action="append", default=[], help="Exclude glob (repeatable)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_path = (root / args.out).resolve()

    includes = DEFAULT_INCLUDE + args.include
    excludes = DEFAULT_EXCLUDE_GLOBS + args.exclude

    n, size = write_zip(root, out_path, includes, excludes)
    print(f"AC.package: {out_path}  files={n}  bytes={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
