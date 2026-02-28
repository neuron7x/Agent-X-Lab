# Agent-X-Lab Monorepo

Production monorepo for AXL UI, Cloudflare Worker BFF, Python engine, and deterministic governance/gate tooling.

## Required CI checks
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

See `docs/06_CI_AND_RELEASE.md` and `build_proof/ci_calibration/` for calibration evidence.
