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

## Pull Request Quality Gates (GitHub)

Branch protection should require these exact workflow names:
- `CodeQL Analysis`
- `Dependency Review`
- `Secret Scan (Gitleaks)`
- `Workflow Hygiene`
- `UI Verify`
- `UI E2E (Playwright)`
- `UI Performance + Bundle Budgets`
- `PROD_SPEC_V2.1 Gate Check (RRD)`

## Documentation

Start at:
- `docs/00_SYSTEM_OVERVIEW.md`
- `docs/98_CONTRACT_INDEX.md`
- `docs/99_CHECKLIST.md`
