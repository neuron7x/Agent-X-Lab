# Agent-X-Lab Monorepo

Production monorepo for AXL UI, Cloudflare Worker BFF, Python engine, and deterministic governance/gate tooling.

## Architecture

- `src/`, `public/`: Vite + React + TypeScript SPA.
- `workers/axl-bff/`: Cloudflare Worker BFF (GitHub/dispatch/forge proxy layer).
- `engine/`: Python engine package and protocol artifacts.
- `udgs_core/`: deterministic governance and validation core.
- `tools/`: supporting developer and prod-spec tooling.
- `docs/`: operational, security, UI, and deployment docs.
- `.github/workflows/`: CI workflows.
- `archive/`: preserved wrapper/snapshot material moved out of active code paths.
- `evidence/`: release/promoted proof artifacts and migration evidence.

## Quickstart

```bash
make bootstrap
make dev-ui
make dev-worker
make test
```

## Environment

- UI requires `VITE_AXL_API_BASE`.
- Protected endpoints also require `VITE_AXL_API_KEY` in UI env and `AXL_API_KEY` in Worker secrets.
- See `.env.example` and `workers/axl-bff/wrangler.toml` comments for setup.

## Documentation

Start at:
- `docs/00_SYSTEM_OVERVIEW.md`
- `docs/98_CONTRACT_INDEX.md`
- `docs/99_CHECKLIST.md`

## Pull Request Quality Gates (GitHub)

To keep PRs deterministic and low-noise, the repository now includes these mandatory GitHub-integrated checks:

- `UI Verify` (`.github/workflows/ui-verify.yml`) for lint, typecheck, unit/a11y tests, and production build.
- `UI E2E (Playwright)` (`.github/workflows/ui-e2e.yml`) for browser smoke validation.
- `UI Performance + Bundle Budgets` (`.github/workflows/ui-perf.yml`) for bundle budgets and Lighthouse CI.
- `Dependency Review` (`.github/workflows/dependency-review.yml`) to block vulnerable dependency deltas in PRs.
- `CodeQL Analysis` (`.github/workflows/codeql-analysis.yml`) to detect security/dataflow issues in TypeScript/JavaScript + Python.
- `Secret Scan` (`.github/workflows/secret-scan.yml`) to prevent credential leaks from entering history.
- `Workflow Hygiene` (`.github/workflows/workflow-hygiene.yml`) to lint GitHub Actions workflows before merge.

Recommended branch protection for `main`:

1. Require pull requests before merge.
2. Require status checks to pass (mark the workflows above as required).
3. Require branches to be up to date before merge.
4. Restrict who can bypass protections.
