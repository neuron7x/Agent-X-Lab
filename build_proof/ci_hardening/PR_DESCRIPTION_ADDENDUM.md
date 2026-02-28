## CI Security + Workflow Quality Gate Hardening Addendum

### WHAT
- SHA-pinned remaining `actions/setup-node@v4` refs in `.github/workflows/ui-perf.yml`.
- Updated Workflow Hygiene permissions to include `pull-requests: read` alongside `contents: read` and `checks: write` for `github-pr-check` reporter.
- Regenerated pin audit with corrected `uses:` detection and confirmed zero `NOT_PINNED` entries.

### WHY
- Remove last CHK-CI-G3 blocker and keep workflow-hygiene least-privilege permissions aligned to check publication behavior.

### EVIDENCE
- `build_proof/ci_hardening/outputs/01_action_pin_audit.txt`
- `build_proof/ci_hardening/outputs/12_not_pinned_check.txt`
- `build_proof/ci_hardening/outputs/15_gh_capability_check.txt`
- `build_proof/ci_hardening/outputs/16_github_api_runs_probe.txt`

### SCOPE
- Edited only workflows/docs/evidence files.

### CURRENT STATUS
- FAIL-CLOSED: verification blocked. This environment cannot query GitHub Actions runs/logs (`gh` missing; API CONNECT 403).
- Operator runbook is provided in `outputs/00_ci_failures_root_cause.txt`.
