# Agent-X-Lab Monorepo

Production monorepo for AXL UI, Cloudflare Worker BFF, Python engine, and deterministic governance/gate tooling.

## Branch-protection required check

Require **`CI Supercheck`** as the single branch-protection status check on PRs. `CI Supercheck` enforces the underlying workflow/job checks contextually (UI, PROD_SPEC, workflow hygiene, and security scans) and fails closed on missing or failed dependencies.

## Supporting workflows monitored by CI Supercheck

- UI Verify
- UI E2E (Playwright)
- UI Performance + Bundle Budgets
- PROD_SPEC_V2.1 Gate Check (RRD)
- Workflow Hygiene
- CodeQL Analysis
- Dependency Review
- Secret Scan (Gitleaks)

See `docs/06_CI_AND_RELEASE.md`, `docs/08_SECURITY_GATES.md`, and `docs/09_BRANCH_PROTECTION.md`.
