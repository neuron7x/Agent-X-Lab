## WHAT
- Reverted and stabilized generated canonical files:
  - `engine/artifacts/titan9/inventory.json`
  - `engine/catalog/index.json`
- Fixed vendor syntax regression in `engine/vendor/scpe-cimqa-2026.3.0/tools/run_interpreter.py` and added a compile regression test (`engine/tests/test_vendor_scpe_syntax.py`).
- Made engine tests hermetic against tracked drift by redirecting drift-causing tests to temporary copied repositories.
- Added PR CI drift guard workflow: `.github/workflows/engine-drift-guard.yml`.

## WHY
To permanently prevent reintroduction of generated workspace drift and ensure engine validation does not mutate tracked repository paths during test execution.

## EVIDENCE
- Repro: `outputs/10_compile_repro.txt`, `outputs/11_pytest_repro.txt`, `outputs/12_git_status_repro.txt`, `outputs/13_git_diff_names_repro.txt`
- Final: `outputs/40_compile_final.txt`, `outputs/41_pytest_final.txt`, `outputs/42_git_status_final.txt`, `outputs/43_git_diff_names_final.txt`
- Canonical revert diff proof: `outputs/20_canonical_revert_diff.txt`
- CI guard workflow: `.github/workflows/engine-drift-guard.yml`

## COMPAT
No shipped runtime behavior changes were introduced; changes are constrained to canonical artifact stabilization, tests, vendor syntax correction, and CI guardrails.
