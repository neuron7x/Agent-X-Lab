# PS — Codex Interpreted Mechanized Quality Agent (CIMQA) v2026.3.0

## 1) State Transition
**Before:** quality state can remain FAIL/UNKNOWN due to missing reports, failing checks, or insufficient SSOT instrumentation; repeated runs can enter Ambiguity Deadlock (S0).

**After:** exactly one of the following outcomes is produced:
- **NORMAL_PR_CREATED**: a normal PR closes owned non-meta gates with EBS-2026 proof bundle, OR
- **META_PR_CREATED**: ERM produces a meta-PR that deterministically patches SSOT under META-EBS-2026.3, OR
- **HARD_REVERT_SSOT**: ERM aborts and restores SSOT from recorded sha256 snapshot (fail-closed).

## 2) Definition of Done (Gate IDs)
Owned non-meta (normal):
- G.SEC.001
- G.IM.001, G.IM.010, G.IM.020, G.IM.030
- G.QM.001, G.QM.010, G.QM.020, G.QM.030, G.QM.040, G.QM.050, G.QM.060
- G.CDX.PR.001, G.CDX.CI.001
- G.EBS.001

Owned meta (ERM):
- G.META.001, G.META.002, G.META.003

DoD (normal): all owned non-meta gates PASS in `REPORTS/gate-decisions.after.json` with EBS-2026 evidence root and `MANIFEST.json`.
DoD (ERM): all G.META.* PASS with META-EBS evidence root and `MANIFEST.META.json`, plus meta PR created OR hard_revert_ssot executed.

## 3) Constraints (Fail-Closed)
- Determinism: every decision is a pure function of (inputs + SSOT + produced reports); randomness forbidden.
- No ACT without DECIDE mapping: each edit references `deficit_fingerprint -> gate_ids -> metrics`.
- Unknown never becomes Pass: UNKNOWN -> FAIL; no inference.
- ERM trigger is necessary and sufficient: `consecutive_fails>=3 AND deficit_severity==S0 AND same_deadlock_fingerprint`.
- ERM is shadow-only: primary worktree is immutable until meta gates PASS.
- ERM can mutate only SSOT allowlisted paths from ERM.yml.
- Halting guarantee: ERM wallclock <= 300s and iterations <= 1; otherwise HARD_REVERT_SSOT.

## 4) Ambiguity Deadlock (S0) Definition
A run is considered in deadlock when:
- the interpreter emits at least one S0 item (deficit severity S0), AND
- the resulting gate state remains FAIL/UNKNOWN across repeated runs, AND
- the deadlock fingerprint is stable for the last 3 evaluations.

**Deadlock fingerprint (DFP):**
- DFP is computed from:
  - deficit_severity
  - primary category (instrumentation/security/tests/etc.)
  - owned_fail_gates (sorted)
  - missing_reports list (sorted)
- Special-case: `missing_reports_count>0 AND deficit_severity==S0 => DFP:missing_reports`.

Artifacts:
- `REPORTS/meta-state.json`: consecutive fails counter, stability flags, last fingerprints.
- `REPORTS/deadlock.json`: normalized deadlock payload + DFP string.

## 5) ERM Transaction Model (Meta-Self-Patch)
ERM does not generate new rules. It selects a predeclared deterministic recipe from ERM.yml.
Each ERM transaction is validated by:
- AST validation (required fields, allowlisted patch paths, sha256 of diffs)
- Contradiction model validation (no new overlapping-action conflicts without strict resolution)
- Invariant preservation validation (PA S4 invariants unchanged)
- Shadow isolation validation (primary `git status --porcelain` clean at meta-validation time)

ERM transaction outputs:
- `REPORTS/erm-txn.selected.yml`
- `REPORTS/erm-patch.result.json`
- `REPORTS/meta-validity.json`
- `MANIFEST.META.json`

## 6) Meta Gates Semantics
- **G.META.001 (AST deterministic + recipe selection)**:
  - Selected transaction exists, AST-valid, deterministic.
- **G.META.002 (META-EBS invariants + regression rate 0)**:
  - Invariants hash preserved; regression_rate==0; meta manifest present and complete.
- **G.META.003 (Shadow isolation)**:
  - Primary worktree unchanged (clean) before any meta gate claims PASS.

## 7) Evidence Standard
### 7.1 Normal EBS-2026
Evidence root:
- `artifacts/evidence/<YYYYMMDD>/<work-id>/`
Required:
- ENV.txt, COMMANDS.txt, REPORTS/, BASELINE/, AFTER/, MANIFEST.json
sha256:
- every required artifact hashed into MANIFEST.json

### 7.2 META-EBS-2026.3
Evidence root:
- `artifacts/evidence/<YYYYMMDD>/<work-id>/META/`
Required:
- `META/ENV.txt`, `META/COMMANDS.txt`, `META/BASELINE/`, `META/AFTER/`, `META/REPORTS/`, `META/MANIFEST.META.json`
Proof objects (sha256-required):
- meta-ast.check.json
- meta-contradictions.json
- invariants.check.json
- isolation.check.json
- halting.check.json

## 8) Deterministic Halting Argument (Operational, Not Theoretical)
ERM does not attempt to solve the general halting problem. Instead it guarantees bounded termination by construction:
- `iterations_max=1`
- `wallclock_seconds_max=300`
- Recipe selection is O(#recipes)
- Patch application is bounded to SSOT allowlist
- Validation phases are fixed and finite
If any phase fails or times out -> HARD_REVERT_SSOT is executed.

## 9) Shadow Isolation Contract
- Shadow worktree root: `.scpe-shadow/<work-id>/`
- Shadow branch: `meta/erm/<work-id>`
- Primary worktree must remain clean through E4 PROVE.META_VALIDITY.
- Only after meta gates PASS may a meta PR be created from the shadow branch.

## 10) Tooling Contracts (Deterministic)
Required ERM tools:
- `tools/observe_meta_state.py` -> emits REPORTS/meta-state.json
- `tools/deadlock_fingerprint.py` -> emits REPORTS/deadlock.json and prints DFP
- `tools/select_erm_txn.py` -> emits REPORTS/erm-txn.selected.yml
- `tools/apply_erm_txn.py` -> creates shadow worktree and emits REPORTS/erm-patch.result.json
- `tools/validate_erm_ast.py` -> emits REPORTS/meta-ast.check.json
- `tools/prove_meta_validity.py` -> emits REPORTS/meta-validity.json (+ derived proof files)
- `tools/make_manifest_meta.py` -> emits META/MANIFEST.META.json

## 11) Security / Redaction
- `SECURITY.redaction.yml` must exist and be enforced before generating any manifest.
- Any token-like patterns must be redacted from logs copied into evidence roots.

## 12) Versioning
- PS.md references v2026.3.0 semantics.
- ERM introduces new mode: `erm-2026.3`.
- Schema versions bumped:
  - CG-2026.3
  - GM-2026.3
  - OH-2026.3
  - ERM-2026.3
  - META-EBS-2026.3
  - IM-2026.3 (when M.META modality is introduced)
