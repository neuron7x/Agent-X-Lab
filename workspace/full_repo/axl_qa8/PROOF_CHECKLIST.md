# Proof Checklist — AXL BFF Integration

## Pre-flight

```bash
# Verify zero ACTUAL fetch/call code to api.github.com (excludes comments)
grep -rn "api\.github\.com" src/ | grep -v "^\s*//" | grep -v "^\s*\*"
# Expected output: NOTHING (empty — acceptance criteria satisfied)

# Confirm api.ts has no live fetch to api.github.com
grep -n "fetch.*api\.github\.com\|= 'https://api\.github\.com'" src/lib/api.ts
# Expected: NOTHING

# Confirm github.ts is a shim only (re-exports, no fetch)
grep -n "^const\|fetch(" src/lib/github.ts
# Expected: NOTHING (only export statements)

# Confirm no token in localStorage keys
grep -rn "localStorage.*token\|token.*localStorage" src/
# Expected: NOTHING (token not stored)

# Confirm types.ts token field is '' sentinel only
grep -A2 "token:" src/lib/types.ts | head -5
# Expected: token: string; // ALWAYS '' — never stored, never sent from browser
```

## Worker local test

```bash
cd workers/axl-bff
npm install
npm run typecheck
# Expected: exit 0, zero TypeScript errors
```

### Start local Worker

```bash
# Set .dev.vars for local secrets
cat > .dev.vars << 'EOF'
GITHUB_TOKEN=ghp_YOUR_PAT_HERE
WEBHOOK_SECRET=test-webhook-secret-32chars
ALLOWED_ORIGINS=http://localhost:8080
GITHUB_OWNER=YOUR_USERNAME
GITHUB_REPO=axl-qa8
GITHUB_VR_BRANCH=vr-state
GITHUB_VR_PATH=ad2026_state/vr/latest.json
EOF

wrangler dev --local
# Worker starts on http://localhost:8787
```

## curl proof commands

### 1. Health check

```bash
curl -s http://localhost:8787/healthz | python3 -m json.tool
```

**Expected response** (HTTP 200):
```json
{
  "ok": true,
  "ts": "2026-02-25T00:00:00.000Z",
  "version": "1.0.0",
  "repo": "YOUR_USERNAME/axl-qa8"
}
```

### 2. VR.json fetch (cache MISS first time)

```bash
curl -sv http://localhost:8787/vr 2>&1 | grep -E "< HTTP|X-AXL-Cache|^{"
```

**Expected headers**:
```
< HTTP/1.1 200 OK
< X-AXL-Cache: MISS
< X-AXL-Cache-Key: vr:YOUR_USERNAME/axl-qa8:vr-state
```

Second call (within TTL):
```bash
curl -sv http://localhost:8787/vr 2>&1 | grep "X-AXL-Cache"
# Expected: X-AXL-Cache: HIT
```

### 3. GitHub proxy — allowed path

```bash
curl -s "http://localhost:8787/gh/repos/YOUR_USERNAME/axl-qa8/actions/runs?per_page=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('total_count:', d.get('total_count'))"
```

**Expected**: prints `total_count: N` (some number)

### 4. GitHub proxy — DENIED path (security test)

```bash
curl -s http://localhost:8787/gh/user | python3 -m json.tool
```

**Expected response** (HTTP 403):
```json
{
  "error": "PROXY_PATH_DENIED",
  "path": "/user",
  "hint": "Only allowlisted GitHub API paths are accessible"
}
```

### 5. Engine dispatch

```bash
curl -s -X POST http://localhost:8787/dispatch/run-engine \
  -H "Content-Type: application/json" \
  -d '{"ref":"main"}' | python3 -m json.tool
```

**Expected response** (HTTP 202):
```json
{
  "ok": true,
  "dispatched": "run-engine",
  "ts": "2026-02-25T00:00:00.000Z"
}
```

### 6. Webhook test — valid signature

```bash
# Generate HMAC signature
SECRET="test-webhook-secret-32chars"
BODY='{"action":"completed","repository":{"full_name":"YOUR_USERNAME/axl-qa8"},"workflow_run":{"head_branch":"main"}}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/.*= /sha256=/')

curl -s -X POST http://localhost:8787/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: workflow_run" \
  -H "X-Hub-Signature-256: $SIG" \
  -d "$BODY" | python3 -m json.tool
```

**Expected response** (HTTP 200):
```json
{
  "ok": true,
  "event": "workflow_run",
  "invalidated": 0
}
```

### 7. Webhook test — invalid signature (security test)

```bash
curl -s -X POST http://localhost:8787/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=badhash" \
  -d '{}' | python3 -m json.tool
```

**Expected** (HTTP 401):
```json
{"error": "SIGNATURE_INVALID"}
```

## Deployment verification (after `wrangler deploy`)

```bash
WORKER_URL="https://axl-bff.YOUR_SUBDOMAIN.workers.dev"

# Health
curl -s "$WORKER_URL/healthz" | python3 -m json.tool

# VR (may 404 until first engine run)
curl -s "$WORKER_URL/vr"
```

## GitHub Actions: manual dispatch test

1. Go to repo → **Actions** → **Run Engine (Dispatch)**
2. Click **Run workflow**
3. Set `dry_run: true` (safe, no push)
4. Wait for completion
5. Check **Artifacts**: should contain `engine-proof-<run_id>` with `latest.json`

**Expected artifact structure**:
```
engine-proof-XXXXXX/
  latest.json           ← VR.json (valid JSON)
  engine_run.log        ← stdout from udgs_core CLI
```

## Acceptance criteria verification

| Criterion | Verify command | Expected |
|-----------|---------------|---------|
| Zero direct GitHub API fetch calls | `grep -rn "fetch.*api\.github\.com" src/` | Empty output |
| No PAT/token in localStorage | `grep -rn "localStorage.*token\|token.*localStorage" src/` | Empty output |
| BFF healthz-based isConfigured | `grep "healthz\|bffStatus" src/hooks/useGitHubSettings.ts \| wc -l` | 5+ lines |
| Worker deny-by-default proxy | `curl .../gh/user` | 403 PROXY_PATH_DENIED |
| Worker CORS fail-closed (no ALLOWED_ORIGINS) | `curl -H "Origin: https://evil.com" .../healthz -sv 2>&1 \| grep Access-Control` | Empty |
| KV cache works | Two consecutive `/vr` calls | Second: `X-AXL-Cache: HIT` |
| Webhook rejects bad sig | curl with wrong X-Hub-Signature-256 | 401 SIGNATURE_INVALID |
| Engine dispatch works | Actions manual run (dry_run=true) | artifact with latest.json |
| No token in browser build | `grep -r "GITHUB_TOKEN" src/` | Empty output |
| vr-state publish: cp not git checkout | `grep "git checkout.*github.sha" .github/workflows/run-engine-dispatch.yml` | Empty |

## No-regression note

### Files modified (Pass 1 + Pass 2 combined)

| File | Change |
|------|--------|
| `src/lib/github.ts` | Re-export shim — no breaking API change |
| `src/lib/types.ts` | `token` field kept as `string` but semantically always `''`; comment documents security contract |
| `src/hooks/useGitHubSettings.ts` | Removed token storage; `isConfigured` now based on BFF healthz probe; localStorage migration removes legacy token |
| `src/components/axl/ConnectRepository.tsx` | Removed PAT input field; shows BFF URL + status; healthz probe on connect |
| `src/components/axl/SettingsPanel.tsx` | Removed PAT input; test button calls BFF healthz; shows BFF endpoint (read-only) |
| `src/pages/Index.tsx` | Updated ConnectRepository props; added bffStatus |
| `workers/axl-bff/src/index.ts` | CORS fail-closed (empty ALLOWED_ORIGINS → no CORS headers); MAX_BODY_BYTES 25KB→1MB |
| `.github/workflows/run-engine-dispatch.yml` | vr-state publish: uses `cp` from temp file; no `git checkout $sha` |
| `PROOF_CHECKLIST.md` | Fixed grep commands to exclude comments; added PAT/token/CORS/workflow checks |

### Files added
- `src/lib/api.ts` — full BFF client; zero api.github.com calls
- `workers/axl-bff/` — Cloudflare Worker (BFF)
- `.github/workflows/run-engine-dispatch.yml` — engine trigger workflow
- `vercel.json` — SPA rewrites + CSP headers
- `.env.example` — env var documentation
- `docs/deploy/vercel.md`, `docs/deploy/cloudflare-worker.md`, `docs/security/threat-model.md`

### Files NOT modified
- `engine/` — untouched
- `udgs_core/` — untouched
- `tools/dao-arbiter/` — untouched
- `system/` configs — untouched
