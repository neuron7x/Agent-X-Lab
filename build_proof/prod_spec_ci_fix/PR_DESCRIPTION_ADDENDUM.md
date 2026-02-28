## WHAT
- Replaced fallback report creation in `prod-spec-gates.yml` with a deterministic Python writer that always emits sorted compact JSON and newline termination when checker output is missing.
- Reworked the report evaluation step to fail closed on missing/invalid report JSON, and to enforce merge blocking only for explicit blockers (G0 FAIL, G3 FAIL, or non-zero checker exit with `rrd_status=PRODUCTION_SPEC_V2.1`).
- Added explicit non-blocking handling for expected non-release states (`rrd_status` != `PRODUCTION_SPEC_V2.1`) when G0/G3 are PASS.

## WHY
- **A (heredoc shell failure):** remove fragile fallback write pattern and use deterministic Python writer.
- **B (deterministic fallback report):** guarantee fallback JSON exists even if checker fails before writing any report.
- **C (merge policy):** prevent NO_RELEASE/non-production states from incorrectly failing merges while retaining hard fail conditions.

## EVIDENCE
- Baseline state: `build_proof/prod_spec_ci_fix/outputs/00_repo_state.txt`
- Before excerpt: `build_proof/prod_spec_ci_fix/outputs/01_before_excerpt.txt`
- After excerpt: `build_proof/prod_spec_ci_fix/outputs/02_after_excerpt.txt`
- CI proof/offload status: `build_proof/prod_spec_ci_fix/outputs/03_ci_run_proof.txt`
- CI run URL: **UNAVAILABLE (gh CLI missing; fail-closed)**

## COMPAT
- Workflow-only change; no runtime behavior changes in `src/`, `workers/`, or `engine/` codepaths.
