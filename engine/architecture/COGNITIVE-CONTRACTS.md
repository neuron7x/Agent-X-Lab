# COGNITIVE CONTRACTS
**Version:** v1.0.0 · **Status:** `ACTIVE` · **Author:** Yaroslav Vasylenko  
**Protocol:** IOPS-2026 · **Layer:** Architecture  
**Created:** 2026-02-20

---

## What This Is

A **formal interface specification** for cognitive artifacts (agents, policies, bundles)
so they can be **composed safely** and validated mechanically.

A “contract” here is the equivalent of an API boundary:
- inputs are typed and required
- outputs are shaped and testable
- failure is explicit and structured
- evidence is mandatory for any non-trivial claim

---

## 1 · Contract Types

### 1.1 Input Contract
Defines the minimum required information to produce a valid output.
- Required fields
- Optional fields
- Scope/exclusion rules
- Unsafe/forbidden requests

### 1.2 Output Contract
Defines the minimum structure of a valid output.
- Required blocks/keys
- Stable identifiers
- Determinism requirements (repeats, seeds, temperatures)

### 1.3 Failure Contract (Fail-Closed)
Defines the only permitted behavior on invalid input:
- `status = FAIL`
- reason + missing fields
- explicit next_action
- no partial “helpful” output that could be misused

### 1.4 Change Contract (Versioning)
Defines what changes are patch/minor/major and what compatibility shims are required.

### 1.5 Evidence Contract
Defines what constitutes a valid claim:
- command, environment, output, artifact path, checksum
- what is prohibited (e.g., secrets in logs)

---

## 2 · Universal Contract Schema (recommended)

```json
{
  "meta": {
    "object": "<name>",
    "version": "<semver>",
    "mode": "fail-closed",
    "protocol": "IOPS-2026",
    "protocol_version": "v1.0.0"
  },
  "input": {
    "required": ["..."],
    "optional": ["..."],
    "forbidden": ["..."]
  },
  "output": {
    "required_blocks": ["..."],
    "determinism": {"temperature": 0.0, "seed": 42, "repeats": 3}
  },
  "failure": {
    "shape": {"status": "FAIL", "reason": "", "missing": [], "next_action": "", "evidence": []}
  },
  "evidence": {
    "required": ["command", "env", "output_excerpt", "artifact_path", "sha256"]
  }
}
```

This schema is descriptive; per-object IO-BUNDLE.md enforces concrete requirements.

---

## 3 · Composition Rules (safe integration)

When composing objects (A → B):
- Outputs of A must satisfy Input Contract of B (validated mechanically).
- Evidence produced by A must be consumable by B (paths + checksums).
- Any ambiguity ⇒ FAIL, not guessing.

---

## 4 · Audit Rules

- Contracts must be reviewable from static text (no hidden behaviors).
- All normative keywords: MUST / MUST NOT / SHOULD / MAY.
- All MUST requirements should have corresponding automated checks (where feasible).

