## WHAT
- Hardened `engine-drift-guard` workflow dependency bootstrap and drift handling:
  - keeps SHA-pinned actions,
  - uses `python -m pip ...` only,
  - captures workspace state in `$RUNNER_TEMP`,
  - updates allowlisted build-proof path for this PR bundle.
- Added hermetic evidence-path redirection support in `engine/tools/run_gate.py` via `AXL_EVIDENCE_ROOT`.
- Strengthened run-gate tests to use isolated temporary evidence roots and kept strict assertions.
- Restored executable-bit invariant in `engine/tests/test_doctor.py` and fixed tracked mode on `engine/scripts/quickstart.sh` (`chmod +x`).

## WHY
- Fixes the CI issue class where engine tests and gate tooling can write into tracked workspace paths.
- Restores strong invariants instead of assertion weakening.
- Maintains fail-closed behavior in CI workflow.

## EVIDENCE
- Baseline/repro capture:
  - `build_proof/pr_engine_ci_hermetic/outputs/10_compile_repro.txt`
  - `build_proof/pr_engine_ci_hermetic/outputs/11_pytest_repro.txt`
  - `build_proof/pr_engine_ci_hermetic/outputs/12_action_pinning_repro.txt`
  - `build_proof/pr_engine_ci_hermetic/outputs/13_git_status_repro.txt`
- Post-fix attempted gate:
  - `build_proof/pr_engine_ci_hermetic/outputs/30_action_pinning_final.txt`
- Current working-tree snapshot:
  - `build_proof/pr_engine_ci_hermetic/outputs/99_git_status_now.txt`

## COMPAT
- Runtime behavior of shipped Engine/UI/Worker is unchanged.
- Changes are CI/test/governance hardening only.
