## CI Calibration Addendum

This PR adds deterministic CI guardrails: pinned action auditing, Python verification coverage, workflow shell hardening, and required-check documentation synchronization. Local proofs are captured in `build_proof/ci_calibration/outputs/`.

### Required workflow set
- UI Verify
- UI E2E (Playwright)
- UI Performance + Bundle Budgets
- PROD_SPEC_V2.1 Gate Check (RRD)
- CodeQL Analysis
- Dependency Review
- Secret Scan (Gitleaks)
- Workflow Hygiene
- Python Verify
- Action Pin Audit

### Status
PF4 (Python local loop) is currently failing due existing engine test regressions; PF6 is blocked because `gh auth status` is not authenticated in this environment.
