"""Minimal JWS (compact) EdDSA/Ed25519 helper.

- Uses Ed25519 signatures (RFC 8037) with JWS compact serialization.
- Intended for signing *small* payloads, e.g. sha256 hex string.

Security notes:
- In production, private keys must be held in HSM/TEE. This helper supports
  loading a raw 32-byte Ed25519 seed from env or file.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - (len(data) % 4)) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


@dataclass(frozen=True)
class JWSParts:
    header_b64: str
    payload_b64: str
    signature_b64: str

    def compact(self) -> str:
        return f"{self.header_b64}.{self.payload_b64}.{self.signature_b64}"


def jws_sign_ed25519(payload: bytes, private_key: Ed25519PrivateKey, header: Dict[str, Any]) -> str:
    """Return JWS compact string."""
    header_json = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h64 = b64url_encode(header_json)
    p64 = b64url_encode(payload)
    signing_input = f"{h64}.{p64}".encode("ascii")
    sig = private_key.sign(signing_input)
    s64 = b64url_encode(sig)
    return f"{h64}.{p64}.{s64}"


def jws_verify_ed25519(jws_compact: str, public_key: Ed25519PublicKey) -> Tuple[bool, Dict[str, Any], bytes]:
    """Verify JWS EdDSA; returns (ok, header_dict, payload_bytes)."""
    try:
        h64, p64, s64 = jws_compact.split(".")
        header = json.loads(b64url_decode(h64))
        payload = b64url_decode(p64)
        sig = b64url_decode(s64)
        signing_input = f"{h64}.{p64}".encode("ascii")
        public_key.verify(sig, signing_input)
        return True, header, payload
    except Exception:
        return False, {}, b""


def priv_from_seed(seed32: bytes) -> Ed25519PrivateKey:
    if len(seed32) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(seed32)


def pub_bytes_raw(public_key: Ed25519PublicKey) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
