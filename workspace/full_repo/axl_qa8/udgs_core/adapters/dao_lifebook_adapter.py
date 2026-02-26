from __future__ import annotations

"""UDGS ↔ DAO-LIFEBOOK adapter.

Goal:
  Convert DAO-LIFEBOOK ProofBundle / FailPacket artifacts into the PROTOCOL_13/DEGC STRICT_JSON packet shape.

Fail-closed:
  - Missing fields, ambiguous mapping, or unrecognized statuses => raise ValueError.

This adapter is intentionally pure (no network I/O)."""

from typing import Any, Dict

from ..strict_json import compute_packet_anchor


def proof_bundle_to_udgs_packet(proof_bundle: Dict[str, Any], *, pre_verification_script: str) -> Dict[str, Any]:
    """Map DAO-LIFEBOOK PROOF_BUNDLE.example.json into UDGS packet.

    Required DAO-LIFEBOOK keys (fail-closed):
      - required_checks_status
      - commit_sha
      - artifact_hashes
    """
    for k in ("required_checks_status", "commit_sha", "artifact_hashes"):
        if k not in proof_bundle:
            raise ValueError(f"Missing key in ProofBundle: {k}")

    status = proof_bundle["required_checks_status"]
    if status not in ("success", "failure", "pending", "skipped"):
        raise ValueError(f"Unrecognized required_checks_status: {status}")

    regression = {
        "suite": ["dao_lifebook.ci_oracle", "dao_lifebook.artifact_hash_check"],
        "expected": {
            "required_checks_status": "success",
            "artifact_hashes_present": True,
        },
        "oracle": "CI",
        "commit_sha": proof_bundle["commit_sha"],
        "required_checks_status": status,
        "artifact_hashes": proof_bundle["artifact_hashes"],
    }

    packet = {
        "FAIL_PACKET": {
            "summary": "DAO-LIFEBOOK proof bundle — ci_oracle gate",
            "signals": ["ci_oracle", "artifact_hash_present"],
            "repro": pre_verification_script,
        },
        "MUTATION_PLAN": {
            "diff_scope": ["(see dao-lifebook artifacts)"],
            "constraints": ["fail-closed", "ssot-external-oracle", "deterministic-anchors"],
        },
        "PRE_VERIFICATION_SCRIPT": pre_verification_script,
        "REGRESSION_TEST_PAYLOAD": regression,
        "SHA256_ANCHOR": "REPLACE_WITH_ACTUAL_SHA256",
    }

    packet["SHA256_ANCHOR"] = compute_packet_anchor(packet)
    return packet
