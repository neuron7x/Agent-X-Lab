# Integration Authority Specification (IAS)
**System**: AXL QA8 / AD-2026  
**Spec target**: PRODUCTION_SPEC_V2.1  
**Generated**: 2026-02-26T00:12:40.423362+00:00

## 0) Executive summary
AXL is already structured around a *gated* release model, but today the **Control Plane is not fully authoritative**:
- `gate_assertions.yaml` is declared *normative*, yet `check_prod_spec_gates.py` contains its own embedded logic and does **not** execute many YAML assertions (notably crypto verification for G6).
- Several artifact contracts drift between “spec text” vs “bundle reality” (naming, formats, required fields).
This IAS defines the **authoritative boundaries** (CP/EP/DP), contract-first interfaces, an FSM orchestration model, and the minimum remediation required for “Control Plane authority” to be true in practice.

## 1) Plane separation

### 1.1 Control Plane (CP) — *authoritative*
**Responsibilities**
- Defines *what is allowed to happen*: policies, gates, artifact schemas, state transitions.
- Produces **policy hashes** (lineage) and blocks execution if CP+evidence are inconsistent.

**Canonical CP objects**
- `artifacts/AC_VERSION.json` (root-of-trust identity + invariants)
- `engine/policies/prod_spec_v2/gate_assertions.yaml` (gate semantics + thresholds)
- JSON Schemas for *every* gate artifact (missing in the promoted bundle; must exist in CP)

### 1.2 Execution Plane (EP) — *stateless + deterministic*
**Responsibilities**
- Performs bounded computations defined by CP: builds, replays, proofs, packaging.
- Produces artifacts *only* per declared output contracts; no side-effects on CP objects.

### 1.3 Delivery Plane (DP) — *materialization only*
**Responsibilities**
- CI/CD runs EP jobs and deploys outputs **only if** CP allows the transition and hashes match.
- DP must not “decide” policy; it only enforces CP decisions.

## 2) Contract-first integration interfaces (normative)

### 2.1 Artifact Interface
Every agent/tool that writes an artifact MUST:
- Validate against a JSON Schema *before* writing (“fail closed”).
- Write atomically: temp file → fsync → rename.
- Include `spec`, `gate`, and `generated_at` (UTC ISO-8601) unless schema explicitly forbids.

### 2.2 No implicit context passing
Agents MUST NOT:
- Read another agent’s working directory, logs, temp files, or caches.
- Infer values from runtime environment unless those values are explicit CP inputs.

Allowed: agents read **only**:
- CP objects (AC_VERSION, gate assertions, schemas, CP lock manifest)
- Their declared predecessor artifacts (explicitly listed in their Input Contract)

### 2.3 Versioned integration contracts
Each artifact schema MUST include:
- `schema_id` (e.g. `AXL_ARTIFACT.build_lock.V1`)
- `spec_version` (e.g. `PRODUCTION_SPEC_V2.1`)
- `compat` rules (forward/backward)

## 3) Orchestration as a Finite State Machine (FSM)

### 3.1 States
- `S0_NO_RELEASE`
- `S1_CP_LOCKED` (CP lock manifest generated)
- `S2_GATES_EVIDENCE_READY` (required artifacts exist + schema-valid)
- `S3_GATECHECK_PASS` (gate checker exit code 0)
- `S4_ARB_APPROVED` (SoD satisfied + memo binds hashes)
- `S5_PRODUCTION_SPEC_V2_1` (promotion allowed)

### 3.2 Transition guards (examples)
- `S0 → S1`: CP lock manifest created; CP hashes recorded.
- `S1 → S2`: All required artifacts present AND schema-valid.
- `S2 → S3`: Gate check PASS (exit code 0) AND report binds CP hash.
- `S3 → S4`: ARB decision memo APPROVED; author/approver/auditor distinct; memo binds `ac_version_sha256` + `gate_report_sha256`.
- `S4 → S5`: Deployment is permitted only if deployed bundle hash == CP-locked hash.

### 3.3 Error model (fail-closed)
Every transition failure emits a single **AXL_FAILURE** record:
- `code` (stable enum)
- `gate_id` (if applicable)
- `blocker` (artifact path + JSON pointer)
- `repro` (single command)

## 4) Deterministic lineage & version lock manifest
CP must compute and publish:

```json
{
  "schema_id": "AXL_CP_LOCK.V1",
  "generated_at": "2026-02-26T00:12:40.423362+00:00",
  "inputs": {
  "artifacts/AC_VERSION.json": "e1e85aee920e4f647944eb3e0af6289500e3f26cc2b459b11cf07f22fbd3f3d4",
  "engine/policies/prod_spec_v2/gate_assertions.yaml": "a8baf2ff835202bbc3d3615c98c8ee692cad8532e00668b739cd0b8179968573",
  "engine/scripts/check_prod_spec_gates.py": "96be6061383bdd0e9d0e44005a3f1b1ae57a4cb3ea165507ba8296a371365934"
}
}
```

Any DP deployment MUST carry this CP lock and refuse to deploy if hashes differ.

## 5) Boundary audit — architectural violations observed in the promoted bundle

### V1 — CP is not authoritative (policy duplication)
`gate_assertions.yaml` is declared normative, but `engine/scripts/check_prod_spec_gates.py` implements checks independently.
**Impact**: policy drift; “PASS” may be meaningless if YAML changes.

### V2 — Crypto verification is not enforced for G6
Gate checker currently treats “file exists” as PASS for AC signature, while YAML describes a real verification step.
**Impact**: false PASS; integrity boundary compromised.

### V3 — Artifact contract drift (names + formats)
Examples:
- YAML references `AC_ROOT_CERT`, bundle contains `AC.root_key.pub`.
- G5 artifacts in the bundle are Markdown where the provided spec text expects JSON.
**Impact**: integration breaks across teams/tools; hidden coupling.

### V4 — Placeholders are not rejected
`AC_VERSION.json.issued_at` is a fixed placeholder date, and `_comment` remains.
**Impact**: provenance ambiguity; audit failure risk.

### V5 — Missing artifact schemas in CP
Promoted bundle lacks JSON schemas for gate artifacts (beyond AC/PB/SSDF in full repo).
**Impact**: boundary validation is weak; fail-closed cannot be guaranteed.

## 6) Minimum remediation to make CP authority real
1. **Single source of truth**: gate checker MUST evaluate gates from `gate_assertions.yaml` (no embedded duplicates).
2. **Schema wall**: add JSON Schemas for *every* gate artifact and validate strictly at read/write boundaries.
3. **Crypto enforcement**: G6 must be either:
   - Verified (public key + JWS check) → PASS, OR
   - Not verifiable in `restricted_sandbox` → `NOT_READY` (not PASS).
4. **Contract stabilization**: freeze artifact names + formats; add an explicit compatibility map only when necessary.
5. **Hash binding everywhere**: gate report and ARB memo must bind:
   - `ac_version_sha256`
   - `cp_lock_sha256`
   - `gate_report_sha256`

---

## Appendix A — CP lock hashes (from promoted bundle)
{
  "artifacts/AC_VERSION.json": "e1e85aee920e4f647944eb3e0af6289500e3f26cc2b459b11cf07f22fbd3f3d4",
  "engine/policies/prod_spec_v2/gate_assertions.yaml": "a8baf2ff835202bbc3d3615c98c8ee692cad8532e00668b739cd0b8179968573",
  "engine/scripts/check_prod_spec_gates.py": "96be6061383bdd0e9d0e44005a3f1b1ae57a4cb3ea165507ba8296a371365934"
}
