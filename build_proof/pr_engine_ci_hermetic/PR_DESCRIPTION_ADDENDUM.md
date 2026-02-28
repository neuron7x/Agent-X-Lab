## WHAT
- Fixed `engine-drift-guard` CI workflow pinning/install/hermetic controls:
  - SHA-pinned `actions/checkout` and `actions/setup-python`.
  - deterministic dependency install including pytest (`engine/requirements-dev.txt` if present, else `pytest pyyaml`).
  - hermetic env (`AXL_TEST_OUTPUT_DIR`, `AXL_ARTIFACTS_ROOT`, `PYTHONDONTWRITEBYTECODE`, `PYTHONHASHSEED`).
  - pre-capture cleanup of stray drift dirs (`engine/artifacts/release-test`, `engine/artifacts/tmp-evidence-test`, `artifacts/agent`).
- Added root wrapper `tools/verify_action_pinning.py` to resolve root tool path mismatch.
- Hermeticized `engine/tests/test_stack.py` to avoid persistent creation of `engine/artifacts/release-test` and `engine/artifacts/tmp-evidence-test` by:
  - moving release output to dedicated `.pytest-*` directories,
  - cleaning those directories inside tests,
  - avoiding previous drift directory names.
- Added autouse hermetic env fixture in `engine/tests/conftest.py` with guard to avoid breaking env-isolation tests.

## WHY
- Eliminate CI/workspace drift and make engine test execution deterministic.
- Ensure action pin audits can be invoked from repo root path expected by gates.

## EVIDENCE
- Baseline: `outputs/00_baseline.txt`
- Pinning before fix: `outputs/01_action_pinning_before.txt`
- Compile: `outputs/10_compile_engine.txt`
- Pytest: `outputs/11_pytest_engine.txt`
- Post-gates status/diff: `outputs/12_git_status_after_gates.txt`, `outputs/13_git_diff_names_after_gates.txt`
- Pinning after fix: `outputs/20_action_pinning_after.txt`

## COMPAT
- No shipped runtime behavior changes; modifications are limited to CI/test/tooling guardrails and hermetic test output handling.
