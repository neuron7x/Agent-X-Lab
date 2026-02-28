## CI Security + Workflow Quality Gate Hardening Addendum

### WHAT changed
- Corrected invalid CodeQL action pins by updating `github/codeql-action/{init,analyze,upload-sarif}` to `89a39a4e59826350b863aa6b6252a07ad50cf83e` (`v4.32.4`).
- Added least-privilege `checks: write` permission to Workflow Hygiene so reviewdog can publish check results with `github-pr-check` reporter.
- Completed remaining SHA pinning in scoped workflows (`ui-verify`, `ui-e2e`, `prod-spec-gates`) including `actions/setup-node` and `actions/upload-artifact` refs.
- Regenerated action pin audit; detected two remaining unpinned refs in `.github/workflows/ui-perf.yml` (outside allowed scope for this task).

### WHY
- Resolve immediate workflow boot failures caused by invalid action refs.
- Align reviewdog reporter behavior with required GitHub Checks API permissions.
- Enforce repository workflow supply-chain policy as far as allowed by current scope, and fail-closed when out-of-scope refs remain.

### EVIDENCE
- Workflow definitions: `.github/workflows/{codeql-analysis.yml,secret-scan.yml,workflow-hygiene.yml,ui-verify.yml,ui-e2e.yml,prod-spec-gates.yml}`
- Pin audit outputs:
  - `build_proof/ci_hardening/outputs/01_action_pin_audit.txt`
  - `build_proof/ci_hardening/outputs/12_not_pinned_check.txt` (shows remaining NOT_PINNED refs)
- Initial failure classes and blocker capture:
  - `build_proof/ci_hardening/outputs/00_ci_failures_root_cause.txt`
  - `build_proof/ci_hardening/outputs/09_gh_cli_check.txt`
  - `build_proof/ci_hardening/outputs/13_ci_log_access_check.txt`
- CI links:
  - https://github.com/neuron7x/Agent-X-Lab/actions/runs/22500920063/job/65187507908?pr=97
  - https://github.com/neuron7x/Agent-X-Lab/actions/runs/22500920069/job/65187507974?pr=97

### SCOPE confirmation
- Changed only workflow/docs/evidence files within allowed scope.
- No runtime source changes.

### CURRENT STATUS (FAIL-CLOSED)
- CI pass-state verification is still blocked in this execution environment because `gh` CLI is unavailable and github.com Actions log access returns HTTP CONNECT 403.
- Therefore checklist items requiring direct CI run-state proof remain FAIL until run logs can be queried from an environment with GitHub access.
