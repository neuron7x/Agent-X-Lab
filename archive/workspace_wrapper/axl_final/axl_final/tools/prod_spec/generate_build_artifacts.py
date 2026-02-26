#!/usr/bin/env python3
"""Generate PROD_SPEC build reproducibility artifacts (G1) and AC hash binding (G0).

Outputs under artifacts/:
  - AC.package
  - rebuilt_artifact              (second build for hash match)
  - artifact.sha256               (sha256 for AC.package)
  - build.lock                    (toolchain + lockfiles snapshot)
  - build.provenance              (build metadata)
  - rebuild.log                   (rebuild comparison summary)

Also updates artifacts/AC_VERSION.json:
  - ac_version_sha256 = sha256(AC.package)

This script performs TWO isolated builds of AC.package using the deterministic
packer (tools/prod_spec/make_ac_package.py) into temp dirs, then compares.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    return p.returncode, out


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(REPO_ROOT), help='Repo root')
    ap.add_argument('--artifacts', default='artifacts', help='Artifacts dir (relative to root)')
    ap.add_argument('--ac-version', default='artifacts/AC_VERSION.json')
    ap.add_argument('--skip-dist-check', action='store_true', help='Do not fail if dist/ missing')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    artifacts_dir = (root / args.artifacts).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    dist = root / 'dist'
    if not args.skip_dist_check and not dist.exists():
        print('ERROR: dist/ missing. Run frontend build (npm ci && npm run build) or import dist from release zip.')
        return 2

    packer = root / 'tools' / 'prod_spec' / 'make_ac_package.py'
    ac_version_path = root / args.ac_version

    # Build #1 (canonical)
    code1, out1 = run([sys.executable, str(packer), '--root', str(root), '--out', str(artifacts_dir / 'AC.package')], cwd=root)
    if code1 != 0:
        print(out1)
        return code1

    # Build #2 (rebuilt_artifact) using temp staging root (copy filtered tree)
    # We use a temp directory to reduce accidental dependency on cwd artifacts.
    with tempfile.TemporaryDirectory(prefix='ac_rebuild_') as td:
        tmp_root = Path(td) / 'repo'
        shutil.copytree(root, tmp_root, dirs_exist_ok=True)
        # Ensure artifacts created by first build are not included
        (tmp_root / 'artifacts' / 'AC.package').unlink(missing_ok=True)
        (tmp_root / 'artifacts' / 'rebuilt_artifact').unlink(missing_ok=True)
        code2, out2 = run([sys.executable, str(tmp_root / 'tools' / 'prod_spec' / 'make_ac_package.py'), '--root', str(tmp_root), '--out', str(tmp_root / 'artifacts' / 'rebuilt_artifact')], cwd=tmp_root)
        if code2 != 0:
            print(out2)
            return code2
        # Copy rebuilt artifact back
        shutil.copy2(tmp_root / 'artifacts' / 'rebuilt_artifact', artifacts_dir / 'rebuilt_artifact')

    ac_pkg = artifacts_dir / 'AC.package'
    rebuilt = artifacts_dir / 'rebuilt_artifact'

    h1 = sha256_file(ac_pkg)
    h2 = sha256_file(rebuilt)

    # artifact.sha256 (for canonical)
    (artifacts_dir / 'artifact.sha256').write_text(f"{h1}  AC.package\n", encoding='utf-8')

    # build.lock
    lock = {
        'generated_at': now_utc(),
        'python': {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
        },
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
        },
        'lockfiles': {
            'package-lock.json_sha256': sha256_file(root / 'package-lock.json') if (root / 'package-lock.json').exists() else None,
            'engine/pyproject.toml_sha256': sha256_file(root / 'engine' / 'pyproject.toml') if (root / 'engine' / 'pyproject.toml').exists() else None,
            'engine/requirements-dev.txt_sha256': sha256_file(root / 'engine' / 'requirements-dev.txt') if (root / 'engine' / 'requirements-dev.txt').exists() else None,
        },
        'notes': [
            'build.lock captures toolchain + lockfile anchors; it is not a substitute for SBOM.',
        ],
    }
    write_json(artifacts_dir / 'build.lock', lock)

    # build.provenance
    prov = {
        'spec': 'PRODUCTION_SPEC_V2.1',
        'generated_at': now_utc(),
        'builder': {
            'tool': 'tools/prod_spec/generate_build_artifacts.py',
            'host': platform.node(),
        },
        'inputs': {
            'repo_root': str(root),
            'dist_present': dist.exists(),
        },
        'outputs': {
            'ac_package': 'artifacts/AC.package',
            'ac_package_sha256': h1,
            'rebuilt_artifact_sha256': h2,
        },
        'reproducibility': {
            'two_clean_builds_same_host': True,
            'bit_identical': h1 == h2,
        },
    }
    write_json(artifacts_dir / 'build.provenance', prov)

    # rebuild.log
    rebuild_log = {
        'generated_at': now_utc(),
        'independent_build_count': 2,
        'definition_of_independent': 'Two builds executed from separate filesystem roots with no shared artifacts directory; same host/toolchain. For cross-host independence, run in a second isolated builder and append evidence.',
        'builds': [
            {'artifact': 'artifacts/AC.package', 'sha256': h1},
            {'artifact': 'artifacts/rebuilt_artifact', 'sha256': h2},
        ],
        'hash_match': h1 == h2,
    }
    write_json(artifacts_dir / 'rebuild.log', rebuild_log)

    # Update AC_VERSION.json ac_version_sha256
    if not ac_version_path.exists():
        print(f"ERROR: {ac_version_path} missing")
        return 3
    acv = load_json(ac_version_path)
    acv['ac_version_sha256'] = h1
    # keep signature as-is; signing handled separately
    write_json(ac_version_path, acv)

    print('OK')
    print(f"AC.package sha256: {h1}")
    print(f"rebuilt_artifact sha256: {h2}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
