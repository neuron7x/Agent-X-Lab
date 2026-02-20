# Error Codes

## Documented deterministic errors

- `E_BACKEND_TORCH_MISSING`
  - Meaning: accelerated backend requested but torch is unavailable.
  - Message: `E_BACKEND_TORCH_MISSING: accelerated backend requires torch. Fix: install torch or use backend='reference'.`
  - Fix: install torch or set `backend='reference'`.
- `E_NO_GIT_NO_BUILD_ID`
  - Meaning: git commit is unavailable and BUILD_ID was not provided.
  - Message: `E_NO_GIT_NO_BUILD_ID: git commit unavailable; set BUILD_ID for deterministic provenance id.`
  - Fix: set `BUILD_ID` in CI or provide git metadata.
- `E_NO_COLLISION_RUNS`
  - Meaning: collision simulation count was not provided for uniqueness testing.
  - Message: `E_NO_COLLISION_RUNS: set TITAN9_COLLISION_RUNS for collision simulation`
  - Fix: set `TITAN9_COLLISION_RUNS` to a positive integer.
- `E_COLLISION_TEST_BUDGET_EXCEEDED`
  - Meaning: uniqueness simulation exceeded the configured runtime budget.
  - Message: `E_COLLISION_TEST_BUDGET_EXCEEDED: uniqueness simulation exceeded runtime budget`
  - Fix: increase `TITAN9_MAX_RUNTIME_SECONDS` or optimize the test/runtime environment.

- `E_README_CONTRACT_VIOLATION`
  - Meaning: README Quickstart contract is not Makefile-SSOT compliant or does not require deterministic seed.
  - Message: `E_README_CONTRACT_VIOLATION: README Quickstart must require PYTHONHASHSEED=0 and run exactly 'make setup', 'make test', 'make proof'.`
  - Fix: update `README.md` Quickstart to include the seed requirement and only `make setup`, `make test`, `make proof`; ensure workflows run `make ci`.

- `E_README_PYTHONHASHSEED_MISSING`
  - Meaning: README Quickstart does not set deterministic PYTHONHASHSEED before python tooling commands.
  - Message: `E_README_PYTHONHASHSEED_MISSING: README Quickstart must export PYTHONHASHSEED=0 before running python tooling.`
  - Fix: add `export PYTHONHASHSEED=0` before python/ruff/mypy/pytest commands in `README.md` Quickstart.
README links to this file as the SSOT for user-facing deterministic error codes.
