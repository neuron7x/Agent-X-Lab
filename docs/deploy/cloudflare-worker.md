# Deploy AXL-BFF to Cloudflare Workers

## Free-tier limits (Cloudflare)

| Resource | Free allowance |
|----------|---------------|
| Requests | 100,000 / day |
| CPU time | 10ms / request |
| KV reads | 100,000 / day |
| KV writes | 1,000 / day |
| KV storage | 1 GB |

More than enough for personal/small-team use.

## First deploy (step by step)

### 1. Install Wrangler

```bash
npm install -g wrangler@3.86.1
wrangler login   # opens browser, authorizes Cloudflare account
```

### 2. Create KV namespace

```bash
cd workers/axl-bff

# Production namespace
wrangler kv:namespace create AXL_KV
# Output: { id: "abc123...", ... }
# → Copy id into wrangler.toml [[kv_namespaces]] id = "abc123..."

# Preview namespace (for wrangler dev)
wrangler kv:namespace create AXL_KV --preview
# → Copy id into wrangler.toml [[kv_namespaces]] preview_id = "xyz..."
```

### 3. Set secrets

```bash
wrangler secret put GITHUB_TOKEN
# → Paste your GitHub PAT
# Required scopes (fine-grained token):
#   Contents: Read-only
#   Actions: Read-only
#   Metadata: Read-only
#   (for repository_dispatch: Contents: Read AND Write OR repo scope on classic PAT)

wrangler secret put WEBHOOK_SECRET
# → Paste a random string (e.g. openssl rand -hex 32)
# Same value goes into GitHub → Settings → Webhooks → Secret

wrangler secret put ALLOWED_ORIGINS
# → https://your-project.vercel.app

wrangler secret put GITHUB_OWNER
# → your-github-username

wrangler secret put GITHUB_REPO
# → axl-qa8

wrangler secret put GITHUB_VR_BRANCH
# → vr-state

wrangler secret put GITHUB_VR_PATH
# → ad2026_state/vr/latest.json
```

### 4. Typecheck and deploy

```bash
cd workers/axl-bff
npm install
npm run typecheck   # must exit 0

wrangler deploy
# Output:
#   ✅ Successfully deployed axl-bff
#   https://axl-bff.<your-subdomain>.workers.dev
```

### 5. Verify health

```bash
curl https://axl-bff.<your-subdomain>.workers.dev/healthz
# Expected:
# {"ok":true,"ts":"2026-...","version":"1.0.0","repo":"owner/axl-qa8"}
```

## GitHub Webhook setup

1. Go to: `https://github.com/<owner>/<repo>/settings/hooks`
2. Click **Add webhook**
3. Settings:
   - **Payload URL**: `https://axl-bff.<your-subdomain>.workers.dev/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: same value you set for `WEBHOOK_SECRET`
   - **Events**: Select individual events:
     - ✅ Push
     - ✅ Workflow runs
     - ✅ Repository dispatch
4. Save

### Test webhook manually

```bash
# Use GitHub CLI
gh api repos/<owner>/<repo>/hooks   # find webhook ID

gh api repos/<owner>/<repo>/hooks/<ID>/test -X POST
# Check Worker logs: wrangler tail axl-bff
```

## KV TTL and invalidation

- Default TTL: **60 seconds** (change `KV_TTL_SEC` var in wrangler.toml)
- Webhook `push` event: **immediate** KV invalidation for that repo prefix
- Cache key format: `vr:<owner>/<repo>:<branch>`

## Rotating secrets

```bash
wrangler secret put GITHUB_TOKEN   # prompts for new value, no downtime
```

## Viewing logs

```bash
wrangler tail axl-bff   # live streaming logs
# Logs show: event type, repo, ref, cache HIT/MISS — never secrets
```
