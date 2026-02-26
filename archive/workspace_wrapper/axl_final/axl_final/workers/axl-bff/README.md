# axl-bff — Cloudflare Worker BFF

Server-side proxy for AXL-UI. Eliminates all direct `api.github.com` calls from the browser.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| GET | `/vr` | Returns VR.json (KV-cached, TTL 60s) |
| POST | `/dispatch/run-engine` | Triggers `repository_dispatch` run-engine |
| GET | `/gh/*` | Allowlist proxy to GitHub API |
| POST | `/webhook/github` | Webhook receiver — invalidates KV |

## Setup (first time)

### 1. Install Wrangler

```bash
npm install -g wrangler@3.86.1
wrangler login
```

### 2. Create KV namespace

```bash
wrangler kv:namespace create AXL_KV
# Copy the ID into wrangler.toml -> [[kv_namespaces]] id

wrangler kv:namespace create AXL_KV --preview
# Copy the preview_id into wrangler.toml -> preview_id
```

### 3. Set secrets (never commit these)

```bash
wrangler secret put GITHUB_TOKEN
# Paste your PAT (required scopes: contents:read, actions:read, actions:write for dispatch)

wrangler secret put WEBHOOK_SECRET
# Paste the same secret you configure in GitHub -> Settings -> Webhooks

wrangler secret put ALLOWED_ORIGINS
# e.g.: https://axl.vercel.app,https://axl-preview.vercel.app

wrangler secret put GITHUB_OWNER
# e.g.: your-github-username

wrangler secret put GITHUB_REPO
# e.g.: axl-qa8

wrangler secret put GITHUB_VR_BRANCH
# e.g.: vr-state

wrangler secret put GITHUB_VR_PATH
# e.g.: ad2026_state/vr/latest.json
```

### 4. Deploy

```bash
cd workers/axl-bff
npm install
npm run typecheck   # must pass with 0 errors
wrangler deploy
```

Expected output:
```
✅ Successfully deployed axl-bff
   https://axl-bff.<your-subdomain>.workers.dev
```

### 5. Configure GitHub Webhook

In your repo: Settings → Webhooks → Add webhook

- **Payload URL**: `https://axl-bff.<your-subdomain>.workers.dev/webhook/github`
- **Content type**: `application/json`
- **Secret**: same value as `WEBHOOK_SECRET`
- **Events**: `push`, `workflow_run`, `repository_dispatch`

### 6. Update UI env

In Vercel project settings (or `.env.local` for dev):
```
VITE_AXL_API_BASE=https://axl-bff.<your-subdomain>.workers.dev
```

## Required GitHub PAT scopes

| Scope | Purpose |
|-------|---------|
| `repo` → `Contents` (read) | Read VR.json, contract files |
| `repo` → `Actions` (read) | Fetch workflow runs, jobs |
| `repo` → `Metadata` (read) | Repo info |
| `repo` → `Contents` (write) | Needed by engine workflow to push VR.json; NOT by Worker PAT |

For `repository_dispatch` specifically: the PAT needs **repo** scope (classic) or **Contents: read+write** for fine-grained.

> **Note**: The Worker PAT only needs read + dispatch. The Actions workflow uses GITHUB_TOKEN (write) separately.

## KV cache behavior

- TTL: 60s (configurable via `KV_TTL_SEC` var)
- On `push`/`workflow_run` webhook: all keys prefixed by `vr:<owner>/<repo>` are deleted immediately
- Key index maintained in `__kv_key_index__` for bulk invalidation
- `X-AXL-Cache: HIT` or `MISS` header on every response

## Security notes

- All GitHub tokens are **Worker secrets** — never reach the browser
- Webhook verified via HMAC-SHA-256 (`X-Hub-Signature-256`)
- Oversized webhook bodies (> 25 KB) rejected with 413
- Proxy allowlist: only `/repos/{owner}/{repo}/*` paths allowed
- CORS: only `ALLOWED_ORIGINS` domains receive `Access-Control-Allow-Origin`
