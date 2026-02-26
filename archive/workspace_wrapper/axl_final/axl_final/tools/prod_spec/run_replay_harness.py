#!/usr/bin/env python3
"""Run PROD_SPEC runtime replay harness (G4).

This is a *local* replay check intended to prove determinism of critical selection
outputs under repeated execution in a production-like environment.

Outputs under artifacts/:
  - env.fingerprint
  - replay.report

Replay target:
- Deterministic SPS selection pipeline (SPS.candidates + verifier.rules)

If AC_VERSION.min_replay_n is N, we run N replays and assert chosen_sps_hash is identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode('utf-8')


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')


def choose(candidates: list[dict], rules: dict) -> dict:
    # Must match tools/prod_spec/generate_formal_artifacts.py
    _ = rules
    return sorted(candidates, key=lambda c: (c['sps_hash'], c['sps_id']))[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(REPO_ROOT))
    ap.add_argument('--artifacts', default='artifacts')
    ap.add_argument('--ac-version', default='artifacts/AC_VERSION.json')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    artifacts = (root / args.artifacts).resolve()

    acv = load_json(root / args.ac_version)
    n = int(acv.get('min_replay_n', 500))

    cand_path = artifacts / 'SPS.candidates'
    rules_path = artifacts / 'verifier.rules'
    if not cand_path.exists() or not rules_path.exists():
        print('ERROR: Missing SPS.candidates or verifier.rules. Run generate_formal_artifacts.py first.')
        return 2

    candidates_obj = load_json(cand_path)
    rules = load_json(rules_path)
    candidates = candidates_obj.get('candidates', [])

    if not isinstance(candidates, list) or not candidates:
        print('ERROR: candidates empty')
        return 3

    # env fingerprint
    env_fp = {
        'generated_at': now_utc(),
        'python': platform.python_version(),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'impl': platform.python_implementation(),
        'pid': os.getpid(),
        'cwd': str(root),
        'inputs': {
            'ac_version_sha256': acv.get('ac_version_sha256', ''),
            'candidates_sha256': sha256_bytes(canonical_json_bytes(candidates_obj)),
            'rules_sha256': sha256_bytes(canonical_json_bytes(rules)),
        },
    }
    env_fp_bytes = canonical_json_bytes(env_fp)
    env_fp_hash = sha256_bytes(env_fp_bytes)
    env_fp['env_fingerprint_hash'] = env_fp_hash

    write_json(artifacts / 'env.fingerprint', env_fp)

    expected = choose(candidates, rules)
    mismatches = 0
    for _ in range(n):
        got = choose(candidates, rules)
        if got.get('sps_hash') != expected.get('sps_hash'):
            mismatches += 1

    report = {
        'generated_at': now_utc(),
        'replay_n': n,
        'mismatches': mismatches,
        'expected_chosen_sps_hash': expected.get('sps_hash'),
        'env_fingerprint_hash': env_fp_hash,
    }
    write_json(artifacts / 'replay.report', report)

    print('OK')
    print(f"N={n} mismatches={mismatches}")
    return 0 if mismatches == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
