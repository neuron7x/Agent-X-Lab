# AXL QA8 — Production Runbook (Phase G)

**Spec**: PRODUCTION_SPEC_V2.1  
**Scope**: UI (Vercel) + BFF Worker (Cloudflare) + Engine (GitHub Actions dispatch)  
**Fail-closed policy**: Any HARD gate FAIL => **NO_RELEASE**.

## 0. Preconditions (must be true before any deploy)

1) **Gates**: `python engine/scripts/check_prod_spec_gates.py ...` yields `RRD=PRODUCTION_SPEC_V2.1`.
2) **Frontend build**: `dist/` exists and is attributable to a specific build run (CI log or imported release archive) via `dist/.dist_source.json`.
3) **Worker secrets** configured (Cloudflare): `GITHUB_TOKEN`, `WEBHOOK_SECRET`, `ALLOWED_ORIGINS`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_VR_BRANCH`, `GITHUB_VR_PATH`, `AXL_API_KEY`, optional forge keys.
4) **Vercel env** configured: `VITE_AXL_API_BASE` (points to Worker URL).

## 1. Deploy order

### 1.1 Deploy Worker (Cloudflare)

1) `cd workers/axl-bff`
2) `npm ci`
3) `npm run build` (if present) or `wrangler deploy`
4) Validate health:
   - `GET /healthz` returns `{ ok: true }`
   - `GET /vr` returns cached VR payload (or a clear error if repo config missing)

### 1.2 Deploy UI (Vercel)

1) Ensure `VITE_AXL_API_BASE` is set to the deployed Worker URL.
2) Trigger Vercel deploy.
3) Validate UI contract checks (manual quick pass):
   - Rate limit state works
   - Polling indicator works
   - No browser calls to `api.github.com`

### 1.3 Enable GitHub webhook invalidation (optional but recommended)

1) Configure GitHub webhook pointing to `POST /webhook/github`.
2) Set webhook secret to match `WEBHOOK_SECRET`.
3) Confirm cache invalidation logs show `invalidated_count > 0` on push events.

## 2. Post-deploy verification checklist

- UI loads and can fetch `/healthz` and `/vr` through BFF.
- Worker rejects non-allowlisted `/gh/*` requests.
- Worker rejects protected endpoints without `X-AXL-Api-Key`.
- Forge endpoints return 401 without key and stream with key.

## 3. Operational notes

- **CORS is fail-closed**: if `ALLOWED_ORIGINS` is empty, browser requests will not receive CORS headers.
- **Rate limiting**: Worker uses KV per-IP windows. Tune only with evidence.
- **Logs**: Keep Worker logs for incident review; redact secrets.
