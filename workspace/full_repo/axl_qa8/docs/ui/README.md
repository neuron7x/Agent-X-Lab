# AXL-UI — Developer Guide

## Quick Start (< 10 min)

```bash
git clone <repo>
cd <repo>
node --version  # must be >= 20
cp .env.example .env.local
# Edit .env.local — set VITE_AXL_API_BASE
npm ci
npm run dev     # → http://localhost:5173
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VITE_AXL_API_BASE` | Prod | BFF Worker URL e.g. `https://axl.workers.dev` |
| `VITE_AXL_API_KEY` | Prod | Must match `AXL_API_KEY` Worker secret |
| `VITE_SENTRY_DSN` | Optional | Sentry error tracking DSN |
| `VITE_COMMIT_SHA` | CI | Set by build pipeline for release tagging |
| `VITE_BUILD_TIME` | CI | ISO timestamp for version stamp |

**Local dev:** `VITE_AXL_API_BASE` falls back to `http://localhost:8787`.

## Architecture

```
src/
  App.tsx                  — QueryClient + Router + Providers
  components/shell/
    AppShell.tsx           — Root layout, nav, command palette mount
    CommandPalette.tsx     — Cmd+K search (cmdk)
  modules/
    status/StatusRoute.tsx — Lazy route chunk
    pipeline/...           — Lazy route chunk
    evidence/...           — Lazy route chunk
    arsenal/...            — Lazy route chunk
    forge/...              — Lazy route chunk
    settings/...           — Lazy route chunk
  lib/
    api.ts                 — BFF client, forge streaming
    schemas/index.ts       — Zod schemas, AXLApiError taxonomy
    queryKeys.ts           — TanStack Query key factory
    observability.ts       — Sentry + structured logging
  hooks/
    useGitHubAPI.ts        — Data aggregation hook
    useLanguage.tsx        — UA/EN i18n
```

### Route Code-Splitting
Every route module is a `React.lazy()` chunk. Initial bundle ≈ 120 kB gzip. Route chunks ≈ 1-4 kB gzip each.

### Data Flow
```
UI → BFF Worker (Cloudflare)
       ├── /vr          → GitHub raw file
       ├── /gh/*        → GitHub API proxy (GET only)
       ├── /dispatch/*  → GitHub Actions trigger
       └── /ai/forge*   → Claude/GPT-5.2/n8n
```

No GitHub tokens or AI keys ever reach the browser.

## Prod Config

```bash
# Vercel
vercel env add VITE_AXL_API_BASE production
vercel env add VITE_AXL_API_KEY  production
vercel --prod
```

Add to `vercel.json` (update CSP connect-src):
```json
"connect-src 'self' https://YOUR-WORKER.workers.dev"
```

## How to Cut a Release

1. Bump `WORKER_VERSION` in `wrangler.toml`
2. `cd workers/axl-bff && wrangler deploy`
3. `git tag ui-v<date>-<sha> && git push --tags`
4. Vercel deploys automatically on push to `main`

## Running Tests

```bash
npm run test:unit          # Vitest (42 tests)
npm run test:e2e           # Playwright (requires npm run build first)
npm run lint               # ESLint (0 errors)
npm run typecheck          # TypeScript (0 errors)
npm run build:analyze      # Bundle visualizer
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `/vr` returns 404 | First engine run not done yet | Run `POST /dispatch/run-engine` |
| Forge returns 401 | `VITE_AXL_API_KEY` mismatch | Match UI key to Worker `AXL_API_KEY` |
| Rate limited (429) | Too many requests from same IP | Wait `retry_after` seconds |
| Build size regression | New dep added without tree-shake | Check `npm run build:analyze` |

## Reading Evidence

After each engine run, `build_proof/ui/` contains:
- `EVD-UI-BASELINE.md` — install + test output
- `EVD-UI-BUNDLE.json` — chunk sizes
- `EVD-UI-TESTS.json` — test results (from CI)
