"""
Deterministic graders for IOPS-2026 object evaluation.

This module is intentionally dependency-light (stdlib only) to keep CI stable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass(frozen=True)
class GradeResult:
    gate_id: str
    passed: bool
    details: str


def _find_section_positions(text: str, section_titles: List[str]) -> Dict[str, int]:
    positions = {}
    for title in section_titles:
        idx = text.find(title)
        positions[title] = idx
    return positions


def DG1_schema(text: str, required_sections: List[str]) -> GradeResult:
    pos = _find_section_positions(text, required_sections)
    missing = [s for s, i in pos.items() if i < 0]
    if missing:
        return GradeResult("DG1", False, f"Missing sections: {missing}")
    # ensure ordered by appearance
    ordered = [pos[s] for s in required_sections]
    if ordered != sorted(ordered):
        return GradeResult("DG1", False, "Sections present but not ordered per IOPS-2026 §2")
    return GradeResult("DG1", True, "All required sections present and ordered")


def DG2_invariants(text: str) -> GradeResult:
    # Require all 7 IOPS invariants to be referenced or enforceable
    required = ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06", "INV-07"]
    missing = [r for r in required if r not in text]
    if missing:
        return GradeResult("DG2", False, f"Missing invariant references: {missing}")
    # Also require explicit fail-closed language
    if "fail-closed" not in text.lower():
        return GradeResult("DG2", False, "Missing explicit fail-closed language")
    return GradeResult("DG2", True, "Invariant references and fail-closed language present")


def DG3_fail_closed_contract(text: str) -> GradeResult:
    # Canonical FAIL object contract must exist with required keys.
    fail_block = re.search(r'"status"\s*:\s*"FAIL"', text)
    if not fail_block:
        return GradeResult("DG3", False, "FAIL contract JSON not found")
    for k in ["reason", "missing", "next_action", "evidence"]:
        if f'"{k}"' not in text:
            return GradeResult("DG3", False, f"FAIL contract missing key: {k}")
    return GradeResult("DG3", True, "FAIL contract exists with required keys")


def DG4_namespace_integrity(text: str, eval_gates: List[str], release_gates: List[str]) -> GradeResult:
    # Ensure declared gates are present and no collisions between DG and G namespaces.
    missing_eval = [g for g in eval_gates if g not in text]
    missing_rel = [g for g in release_gates if g not in text]
    if missing_eval or missing_rel:
        return GradeResult("DG4", False, f"Missing gates: eval={missing_eval}, release={missing_rel}")
    # Collision: any gate id appearing in both lists (should be none)
    collisions = sorted(set(eval_gates).intersection(set(release_gates)))
    if collisions:
        return GradeResult("DG4", False, f"Gate namespace collision: {collisions}")
    # Also ensure we don't have ambiguous "G1" inside "DG1" only; enforce word boundaries
    # (best-effort; not a hard fail if present)
    return GradeResult("DG4", True, "Gate namespaces declared and non-colliding")


def DG5_token_budget(text: str, min_max_tokens: int) -> GradeResult:
    m = re.search(r"max_tokens:\s*(\d+)", text)
    if not m:
        return GradeResult("DG5", False, "max_tokens declaration not found")
    val = int(m.group(1))
    if val < min_max_tokens:
        return GradeResult("DG5", False, f"max_tokens too low: {val} < {min_max_tokens}")
    return GradeResult("DG5", True, f"max_tokens={val} meets minimum")


def DG6_evidence_bundle_spec(text: str) -> GradeResult:
    # Require evidence bundle root and sha256 mention
    if "artifacts/evidence" not in text:
        return GradeResult("DG6", False, "Evidence bundle root path not specified")
    if "sha256" not in text.lower():
        return GradeResult("DG6", False, "sha256 requirement not specified")
    if "ENV.txt" not in text:
        return GradeResult("DG6", False, "ENV.txt not required in evidence bundle")
    return GradeResult("DG6", True, "Evidence bundle spec includes root, sha256, and ENV.txt")


def DG7_secret_clean(text: str) -> GradeResult:
    # Must require gitleaks pass and forbid secret echo
    t = text.lower()
    if "gitleaks" not in t:
        return GradeResult("DG7", False, "gitleaks requirement not found")
    if "never output secrets" not in t and "never output secret" not in t:
        return GradeResult("DG7", False, "Explicit prohibition on secret output not found")
    return GradeResult("DG7", True, "Secret-clean policy present")


def grade_all(text: str, required_sections: List[str], eval_gates: List[str], release_gates: List[str], min_max_tokens: int) -> List[GradeResult]:
    graders = [
        lambda: DG1_schema(text, required_sections),
        lambda: DG2_invariants(text),
        lambda: DG3_fail_closed_contract(text),
        lambda: DG4_namespace_integrity(text, eval_gates, release_gates),
        lambda: DG5_token_budget(text, min_max_tokens),
        lambda: DG6_evidence_bundle_spec(text),
        lambda: DG7_secret_clean(text),
    ]
    return [g() for g in graders]
