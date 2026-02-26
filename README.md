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

All product and operations documentation lives under `docs/`.
