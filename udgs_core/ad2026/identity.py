"""
udgs_core.ad2026.identity
=========================
AD-2026 Layer 0 — Agentic Trust & Identity (ZTO)

Implements:
  - AAID  : Agent Authentication Identity (short-lived keypair + chain)
  - ACRootKey : Architecture Constitution root signing key
  - JWS   : compact JSON Web Signature (HMAC-SHA256, stdlib-only)
  - APB   : Attested Proof Bundle header (hash-chained, JWS-signed)
  - ZTO   : Zero-Trust Orchestration verification

All cryptography uses stdlib (hmac + hashlib + secrets).
ENV_CLASS is recorded automatically:
  - NO_TEE when running outside a hardware-backed TPM/TEE (standard case)
  - TEE    when hardware attestation is externally injected
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

ENV_CLASS_NO_TEE = "NO_TEE"
ENV_CLASS_TEE    = "TEE"
AD2026_VERSION   = "2026.02.25"
JWS_ALG          = "HS256"          # HMAC-SHA256 (stdlib; upgrade to EdDSA with cryptography lib)
AAID_KEY_BYTES   = 32               # 256-bit ephemeral key material


# ──────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _sha256hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ──────────────────────────────────────────────
# Evidence Reference  §REF:<KIND>#<ID>#<SHA256>
# ──────────────────────────────────────────────

class EvidenceKind(str, Enum):
    LOG     = "LOG"
    TRACE   = "TRACE"
    DOC     = "DOC"
    ADR     = "ADR"
    RFC     = "RFC"
    SPEC    = "SPEC"
    TEST    = "TEST"
    BUILD   = "BUILD"
    ATTEST  = "ATTEST"
    METRIC  = "METRIC"
    DIFF    = "DIFF"
    INCIDENT= "INCIDENT"


@dataclass(frozen=True)
class EvidenceRef:
    kind:   EvidenceKind
    id:     str
    sha256: str        # content hash of referenced artifact

    def __str__(self) -> str:
        return f"§REF:{self.kind.value}#{self.id}#{self.sha256}"

    @classmethod
    def from_str(cls, s: str) -> "EvidenceRef":
        if not s.startswith("§REF:"):
            raise ValueError(f"Invalid EvidenceRef: {s!r}")
        _, rest = s.split("§REF:", 1)
        kind_str, id_, sha256 = rest.split("#", 2)
        return cls(kind=EvidenceKind(kind_str), id=id_, sha256=sha256)

    @classmethod
    def from_bytes(cls, kind: EvidenceKind, id_: str, data: bytes) -> "EvidenceRef":
        return cls(kind=kind, id=id_, sha256=_sha256hex(data))

    def as_dict(self) -> Dict[str, str]:
        return {"ref": str(self), "kind": self.kind.value, "id": self.id, "sha256": self.sha256}


# ──────────────────────────────────────────────
# AAID — Agent Authentication Identity
# ──────────────────────────────────────────────

@dataclass
class AAID:
    """
    Short-lived agent keypair.  In production upgrade _key_material to
    hardware-backed key via TPM/TEE; set env_class = TEE accordingly.
    """
    agent_id:    str
    env_class:   str
    created_utc: str
    _secret_key: bytes = field(repr=False, compare=False)

    @classmethod
    def generate(cls, agent_id: str, *, env_class: str = ENV_CLASS_NO_TEE) -> "AAID":
        secret = secrets.token_bytes(AAID_KEY_BYTES)
        return cls(
            agent_id=agent_id,
            env_class=env_class,
            created_utc=_utc_now(),
            _secret_key=secret,
        )

    @property
    def public_id(self) -> str:
        """Stable, non-secret identifier derived from key material."""
        return _sha256hex(self._secret_key)[:32]

    def sign(self, payload: bytes) -> str:
        """Return HMAC-SHA256 MAC over payload (hex)."""
        return hmac.new(self._secret_key, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, mac: str) -> bool:
        expected = self.sign(payload)
        return hmac.compare_digest(expected, mac)

    def as_public_dict(self) -> Dict[str, str]:
        return {
            "agent_id":    self.agent_id,
            "public_id":   self.public_id,
            "env_class":   self.env_class,
            "created_utc": self.created_utc,
            "alg":         JWS_ALG,
        }


# ──────────────────────────────────────────────
# AC Root Key — Architecture Constitution signing key
# ──────────────────────────────────────────────

@dataclass
class ACRootKey:
    """
    Offline root key for signing Architecture Constitution versions.
    Production: store in air-gapped HSM.  Here: file-backed secret.
    """
    key_id:      str
    created_utc: str
    _secret_key: bytes = field(repr=False, compare=False)

    @classmethod
    def generate(cls, key_id: str = "AC_ROOT_KEY") -> "ACRootKey":
        return cls(
            key_id=key_id,
            created_utc=_utc_now(),
            _secret_key=secrets.token_bytes(AAID_KEY_BYTES),
        )

    @classmethod
    def load(cls, path: str) -> "ACRootKey":
        with open(path, "rb") as f:
            data = json.loads(f.read())
        return cls(
            key_id=data["key_id"],
            created_utc=data["created_utc"],
            _secret_key=bytes.fromhex(data["_secret_hex"]),
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(json.dumps({
                "key_id": self.key_id,
                "created_utc": self.created_utc,
                "_secret_hex": self._secret_key.hex(),
            }, indent=2).encode())

    def sign_ac(self, ac_canonical_bytes: bytes) -> str:
        return hmac.new(self._secret_key, ac_canonical_bytes, hashlib.sha256).hexdigest()

    def verify_ac(self, ac_canonical_bytes: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign_ac(ac_canonical_bytes), signature)


# ──────────────────────────────────────────────
# JWS — compact JSON Web Signature (HMAC-SHA256)
# ──────────────────────────────────────────────

def jws_sign(payload: Dict[str, Any], aaid: AAID) -> str:
    """
    Produce compact JWS: base64url(header).base64url(payload).signature
    where signature = HMAC-SHA256(key, header.payload)
    """
    header = {"alg": JWS_ALG, "kid": aaid.public_id, "typ": "AD2026+JWT"}
    h_enc = _b64url(_canonical_json(header))
    p_enc = _b64url(_canonical_json(payload))
    signing_input = f"{h_enc}.{p_enc}".encode("ascii")
    sig = aaid.sign(signing_input)
    return f"{h_enc}.{p_enc}.{sig}"


def jws_verify(token: str, aaid: AAID) -> tuple[bool, Dict[str, Any]]:
    """
    Verify compact JWS against AAID.
    Returns (valid: bool, payload: dict)
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False, {}
        h_enc, p_enc, sig = parts
        signing_input = f"{h_enc}.{p_enc}".encode("ascii")
        valid = aaid.verify(signing_input, sig)
        payload = json.loads(base64.urlsafe_b64decode(p_enc + "=="))
        return valid, payload
    except Exception:
        return False, {}


# ──────────────────────────────────────────────
# APB Header — Attested Proof Bundle
# ──────────────────────────────────────────────

@dataclass
class APBHeader:
    """
    Immutable header for every Attested Proof Bundle.
    Must be JWS-signed and hash-chained to previous bundle.
    """
    bundle_id:              str
    aaid_public_id:         str
    agent_id:               str
    timestamp_utc:          str
    monotonic_counter:      int
    sha256_input_state:     str
    sha256_output_state:    str
    sha256_ac_version:      str
    toolchain_pins_hash:    str
    env_fingerprint_hash:   str
    gate_results_hash:      str
    prev_bundle_hash:       str    # "" for genesis
    evidence_refs:          List[str] = field(default_factory=list)
    jws_token:              str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        d = self.as_dict()
        d.pop("jws_token", None)   # exclude signature from its own payload
        return _canonical_json(d)

    def sha256(self) -> str:
        return _sha256hex(self.canonical_bytes())


class APBChain:
    """
    Hash-chained sequence of Attested Proof Bundles.
    append() verifies chain continuity.
    """

    def __init__(self, aaid: AAID, ac_version_sha256: str,
                 toolchain_pins_hash: str, env_fingerprint_hash: str) -> None:
        self.aaid = aaid
        self.ac_version_sha256 = ac_version_sha256
        self.toolchain_pins_hash = toolchain_pins_hash
        self.env_fingerprint_hash = env_fingerprint_hash
        self._chain: List[APBHeader] = []
        self._counter = 0

    def append(
        self,
        input_state:   Any,
        output_state:  Any,
        gate_results:  Dict[str, str],
        evidence_refs: Optional[List[EvidenceRef]] = None,
    ) -> APBHeader:
        self._counter += 1
        prev_hash = self._chain[-1].sha256() if self._chain else ""

        payload = {
            "sha256_input_state":  _sha256hex(_canonical_json(input_state)),
            "sha256_output_state": _sha256hex(_canonical_json(output_state)),
            "sha256_ac_version":   self.ac_version_sha256,
            "toolchain_pins_hash": self.toolchain_pins_hash,
            "env_fingerprint_hash": self.env_fingerprint_hash,
            "gate_results_hash":   _sha256hex(_canonical_json(gate_results)),
            "prev_bundle_hash":    prev_hash,
            "monotonic_counter":   self._counter,
            "agent_id":            self.aaid.agent_id,
            "timestamp_utc":       _utc_now(),
        }
        token = jws_sign(payload, self.aaid)

        header = APBHeader(
            bundle_id=f"APB-{self.aaid.public_id[:8]}-{self._counter:04d}",
            aaid_public_id=self.aaid.public_id,
            agent_id=self.aaid.agent_id,
            timestamp_utc=payload["timestamp_utc"],
            monotonic_counter=self._counter,
            sha256_input_state=payload["sha256_input_state"],
            sha256_output_state=payload["sha256_output_state"],
            sha256_ac_version=self.ac_version_sha256,
            toolchain_pins_hash=self.toolchain_pins_hash,
            env_fingerprint_hash=self.env_fingerprint_hash,
            gate_results_hash=payload["gate_results_hash"],
            prev_bundle_hash=prev_hash,
            evidence_refs=[str(r) for r in (evidence_refs or [])],
            jws_token=token,
        )
        self._chain.append(header)
        return header

    def verify_chain(self) -> tuple[bool, List[str]]:
        """Verify hash-chain continuity and JWS signatures for all bundles."""
        errors: List[str] = []
        prev_hash = ""
        for i, bundle in enumerate(self._chain):
            # Chain continuity
            if bundle.prev_bundle_hash != prev_hash:
                errors.append(f"Bundle {i}: chain break — expected prev={prev_hash[:16]}… got {bundle.prev_bundle_hash[:16]}…")
            # JWS signature
            valid, _ = jws_verify(bundle.jws_token, self.aaid)
            if not valid:
                errors.append(f"Bundle {i}: JWS signature invalid")
            prev_hash = bundle.sha256()
        return len(errors) == 0, errors

    def head(self) -> Optional[APBHeader]:
        return self._chain[-1] if self._chain else None

    def __len__(self) -> int:
        return len(self._chain)


# ──────────────────────────────────────────────
# ZTO — Zero-Trust Orchestration verification
# ──────────────────────────────────────────────

def zto_verify(
    bundle: APBHeader,
    trusted_aaid: AAID,
    ac_root_key: ACRootKey,
    ac_canonical_bytes: bytes,
    ac_signature: str,
    expected_prev_hash: str,
) -> tuple[bool, List[str]]:
    """
    AD-2026 §0.3 Zero-Trust Orchestration check.
    Returns (valid, errors).

    Verifies:
      1. JWS signature verifies to trusted_aaid
      2. ac_version_sha256 matches actual AC bytes
      3. AC signature verifies to ac_root_key
      4. prev_bundle_hash continuity
    """
    errors: List[str] = []

    # 1. JWS
    valid_jws, _ = jws_verify(bundle.jws_token, trusted_aaid)
    if not valid_jws:
        errors.append("ZTO: JWS signature failed — AAID chain mismatch")

    # 2. AC version hash
    actual_ac_sha256 = _sha256hex(ac_canonical_bytes)
    if bundle.sha256_ac_version != actual_ac_sha256:
        errors.append(
            f"ZTO: AC version hash mismatch — "
            f"bundle={bundle.sha256_ac_version[:16]}… actual={actual_ac_sha256[:16]}…"
        )

    # 3. AC root key signature
    if not ac_root_key.verify_ac(ac_canonical_bytes, ac_signature):
        errors.append("ZTO: AC not signed by AC_ROOT_KEY")

    # 4. Hash-chain continuity
    if bundle.prev_bundle_hash != expected_prev_hash:
        errors.append(
            f"ZTO: PB hash-chain break — "
            f"expected={expected_prev_hash[:16]}… got={bundle.prev_bundle_hash[:16]}…"
        )

    return len(errors) == 0, errors
