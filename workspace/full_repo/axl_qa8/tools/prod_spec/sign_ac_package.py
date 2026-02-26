#!/usr/bin/env python3
"""Sign artifacts/AC.package digest with Ed25519 and write AC.signature.jws.

This produces:
  - artifacts/AC.signature.jws
  - artifacts/AC.root_key.pub          (raw 32-byte public key, base64url)
  - updates artifacts/AC_VERSION.json.signature (alg=EdDSA, kid=...)

Key material:
- Preferred: provide a 32-byte Ed25519 seed via env var AC_SIGNING_SEED_B64URL
  (base64url, no padding). This keeps signing deterministic across builders.
- Alternative: provide AC_SIGNING_SEED_HEX (64 hex chars).
- If neither is set, the script can generate an EPHEMERAL dev key only when
  --allow-ephemeral is passed.

Security:
- Do NOT use ephemeral keys for production. Store signing keys in HSM/TEE.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
import sys

from pathlib import Path

# Ensure repo root is on sys.path so tools.prod_spec imports work when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.prod_spec._jws_ed25519 import jws_sign_ed25519, priv_from_seed, pub_bytes_raw, b64url_encode

REPO_ROOT = Path(__file__).resolve().parents[2]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _seed_from_env() -> bytes | None:
    b64u = os.environ.get('AC_SIGNING_SEED_B64URL', '').strip()
    if b64u:
        # base64url without padding
        pad = '=' * ((4 - (len(b64u) % 4)) % 4)
        return base64.urlsafe_b64decode((b64u + pad).encode('ascii'))
    hx = os.environ.get('AC_SIGNING_SEED_HEX', '').strip().lower()
    if hx:
        return bytes.fromhex(hx)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(REPO_ROOT))
    ap.add_argument('--artifacts', default='artifacts')
    ap.add_argument('--ac-version', default='artifacts/AC_VERSION.json')
    ap.add_argument('--kid', default='ac-root-key-2026-ed25519')
    ap.add_argument('--allow-ephemeral', action='store_true')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    artifacts = (root / args.artifacts).resolve()
    ac_pkg = artifacts / 'AC.package'
    if not ac_pkg.exists():
        print('ERROR: artifacts/AC.package not found. Run generate_build_artifacts.py first.')
        return 2

    seed = _seed_from_env()
    if seed is None:
        if not args.allow_ephemeral:
            print('ERROR: No signing seed provided. Set AC_SIGNING_SEED_B64URL or AC_SIGNING_SEED_HEX, or pass --allow-ephemeral for a DEV-only signature.')
            return 3
        seed = os.urandom(32)

    if len(seed) != 32:
        print('ERROR: signing seed must be exactly 32 bytes')
        return 4

    priv = priv_from_seed(seed)
    pub = priv.public_key()

    digest_hex = sha256_file(ac_pkg).encode('ascii')

    header = {
        'alg': 'EdDSA',
        'kid': args.kid,
        'typ': 'JWS',
    }

    jws = jws_sign_ed25519(digest_hex, priv, header)

    # Write signature file
    (artifacts / 'AC.signature.jws').write_text(jws + '\n', encoding='utf-8')

    # Write public key for verification (base64url raw bytes)
    pub_raw = pub_bytes_raw(pub)
    (artifacts / 'AC.root_key.pub').write_text(b64url_encode(pub_raw) + '\n', encoding='utf-8')

    # Update AC_VERSION.json signature block + issuer digest
    acv_path = root / args.ac_version
    acv = load_json(acv_path)
    acv['ac_version_sha256'] = sha256_file(ac_pkg)
    acv['signature'] = {
        'jws': jws,
        'alg': 'EdDSA',
        'kid': args.kid,
        'signed_at': now_utc(),
        '_note': 'Ed25519 JWS over sha256(AC.package) hex string payload. For production, keep private key in HSM/TEE and rotate kid via registry.',
    }
    write_json(acv_path, acv)

    print('OK')
    print(f"kid: {args.kid}")
    print(f"ac_sha256: {acv['ac_version_sha256']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
