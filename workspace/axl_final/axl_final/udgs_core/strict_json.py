from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .anchors import sha256_json


REQUIRED_KEYS = [
    "FAIL_PACKET",
    "MUTATION_PLAN",
    "PRE_VERIFICATION_SCRIPT",
    "REGRESSION_TEST_PAYLOAD",
    "SHA256_ANCHOR",
]

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

FAIL_PACKET_REQUIRED_KEYS = ["summary", "signals", "repro"]
MUTATION_PLAN_REQUIRED_KEYS = ["diff_scope", "constraints"]
REGRESSION_REQUIRED_KEYS = ["suite", "expected"]


@dataclass
class ValidationError:
    path: str
    message: str


def _is_obj(x: Any) -> bool:
    return isinstance(x, dict)


def _is_str(x: Any) -> bool:
    return isinstance(x, str)


def _is_list_of_nonempty_str(x: Any) -> bool:
    return isinstance(x, list) and len(x) > 0 and all(isinstance(i, str) and i.strip() for i in x)


def _nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _require_keys(obj: Dict[str, Any], keys: List[str], root: str, errors: List[ValidationError]) -> None:
    for k in keys:
        if k not in obj:
            errors.append(ValidationError(f"{root}.{k}", "Missing required key"))


def packet_anchor_payload(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical payload used to derive SHA256_ANCHOR (self-anchor without circularity).

    Contract:
      - include only REQUIRED_KEYS except SHA256_ANCHOR
      - preserve nested content exactly
      - final hashing canonicalization is handled by anchors.sha256_json (sorted keys, compact JSON)
    """
    if not isinstance(obj, dict):
        raise TypeError("Packet must be a dict")
    base = deepcopy(obj)
    base.pop("SHA256_ANCHOR", None)
    return {k: base[k] for k in REQUIRED_KEYS if k != "SHA256_ANCHOR" and k in base}


def compute_packet_anchor(obj: Dict[str, Any]) -> str:
    return sha256_json(packet_anchor_payload(obj))


def validate_packet(obj: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
    errors: List[ValidationError] = []

    if not _is_obj(obj):
        return False, [ValidationError("$", "Packet must be a JSON object")]

    for k in REQUIRED_KEYS:
        if k not in obj:
            errors.append(ValidationError(f"$.{k}", "Missing required key"))

    # type checks
    if "FAIL_PACKET" in obj and not _is_obj(obj["FAIL_PACKET"]):
        errors.append(ValidationError("$.FAIL_PACKET", "Must be an object"))
    if "MUTATION_PLAN" in obj and not _is_obj(obj["MUTATION_PLAN"]):
        errors.append(ValidationError("$.MUTATION_PLAN", "Must be an object"))
    if "PRE_VERIFICATION_SCRIPT" in obj and not _is_str(obj["PRE_VERIFICATION_SCRIPT"]):
        errors.append(ValidationError("$.PRE_VERIFICATION_SCRIPT", "Must be a string"))
    if "REGRESSION_TEST_PAYLOAD" in obj and not _is_obj(obj["REGRESSION_TEST_PAYLOAD"]):
        errors.append(ValidationError("$.REGRESSION_TEST_PAYLOAD", "Must be an object"))
    if "SHA256_ANCHOR" in obj and not _is_str(obj["SHA256_ANCHOR"]):
        errors.append(ValidationError("$.SHA256_ANCHOR", "Must be a string"))

    # STRICT_JSON: no extra top-level keys allowed (fail-closed)
    extra = [k for k in obj.keys() if k not in REQUIRED_KEYS]
    if extra:
        errors.append(ValidationError("$", f"Extra keys not allowed: {extra}"))

    # nested contract checks (fail-closed)
    if _is_obj(obj.get("FAIL_PACKET")):
        fp = obj["FAIL_PACKET"]
        _require_keys(fp, FAIL_PACKET_REQUIRED_KEYS, "$.FAIL_PACKET", errors)
        if "summary" in fp and not _nonempty_str(fp["summary"]):
            errors.append(ValidationError("$.FAIL_PACKET.summary", "Must be a non-empty string"))
        if "repro" in fp and not _nonempty_str(fp["repro"]):
            errors.append(ValidationError("$.FAIL_PACKET.repro", "Must be a non-empty string"))
        if "signals" in fp and not _is_list_of_nonempty_str(fp["signals"]):
            errors.append(ValidationError("$.FAIL_PACKET.signals", "Must be a non-empty array of non-empty strings"))

    if _is_obj(obj.get("MUTATION_PLAN")):
        mp = obj["MUTATION_PLAN"]
        _require_keys(mp, MUTATION_PLAN_REQUIRED_KEYS, "$.MUTATION_PLAN", errors)
        if "diff_scope" in mp and not _is_list_of_nonempty_str(mp["diff_scope"]):
            errors.append(ValidationError("$.MUTATION_PLAN.diff_scope", "Must be a non-empty array of non-empty strings"))
        if "constraints" in mp and not _is_list_of_nonempty_str(mp["constraints"]):
            errors.append(ValidationError("$.MUTATION_PLAN.constraints", "Must be a non-empty array of non-empty strings"))

    if "PRE_VERIFICATION_SCRIPT" in obj and _is_str(obj["PRE_VERIFICATION_SCRIPT"]) and not obj["PRE_VERIFICATION_SCRIPT"].strip():
        errors.append(ValidationError("$.PRE_VERIFICATION_SCRIPT", "Must be a non-empty string"))

    if _is_obj(obj.get("REGRESSION_TEST_PAYLOAD")):
        rp = obj["REGRESSION_TEST_PAYLOAD"]
        _require_keys(rp, REGRESSION_REQUIRED_KEYS, "$.REGRESSION_TEST_PAYLOAD", errors)
        if "suite" in rp and not _is_list_of_nonempty_str(rp["suite"]):
            errors.append(ValidationError("$.REGRESSION_TEST_PAYLOAD.suite", "Must be a non-empty array of non-empty strings"))
        if "expected" in rp:
            if not _is_obj(rp["expected"]):
                errors.append(ValidationError("$.REGRESSION_TEST_PAYLOAD.expected", "Must be an object"))
            elif len(rp["expected"]) == 0:
                errors.append(ValidationError("$.REGRESSION_TEST_PAYLOAD.expected", "Must not be empty"))

    if "SHA256_ANCHOR" in obj and _is_str(obj["SHA256_ANCHOR"]):
        anchor = obj["SHA256_ANCHOR"]
        if not SHA256_RE.match(anchor):
            errors.append(ValidationError("$.SHA256_ANCHOR", "Must be 64 lowercase hex chars (SHA-256)"))
        else:
            # only compare anchor when the packet has all required keys and no top-level extras to avoid false context
            if all(k in obj for k in REQUIRED_KEYS) and not extra:
                expected_anchor = compute_packet_anchor(obj)
                if anchor != expected_anchor:
                    errors.append(ValidationError("$.SHA256_ANCHOR", f"Anchor mismatch (expected {expected_anchor})"))

    return (len(errors) == 0), errors


def load_and_validate(path: str) -> Tuple[bool, Dict[str, Any], List[ValidationError]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    ok, errs = validate_packet(obj)
    return ok, obj, errs
