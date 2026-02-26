# Happy-path example — two-PR readiness plan (illustrative)

Input: repo has flaky tests and unpinned toolchain.
Expected: output includes INVENTORY_JSON, GATE_MATRIX, PR_PLAN with PR1=determinism/toolchain, PR2=flake elimination; each with evidence+rollback.
