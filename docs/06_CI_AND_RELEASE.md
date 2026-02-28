# 06 CI and Release {#ci-release}

## Required checks (exact workflow names)
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

See workflow definitions in `.github/workflows/*.yml` and CI proof links in `build_proof/ci_calibration/ci_links.txt`.
