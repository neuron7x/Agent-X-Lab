# AXL QA8 — Production Deployment Guide
**Status**: `PRODUCTION_SPEC_V2.1` · **rrd_status**: PRODUCTION_SPEC_V2.1 · **All 9 HARD gates: PASS**  
**Promoted**: 2026-02-26 · **AC**: AC-AD2026AXLV21 v2.1.0 · **Grade**: PRODUCTION_SPEC_V2.1

---

## Pre-flight verification (запускай першим)

```bash
python3 engine/scripts/check_prod_spec_gates.py \
  --ac artifacts/AC_VERSION.json \
  --pb-dir ad2026_state/pb/ \
  --ssdf artifacts/SSDF.map \
  --out artifacts/gate_check.report.json

# Очікуваний результат:
# RRD: PRODUCTION_SPEC_V2.1
# Exit code: 0
```

---

## Step 1 — Deploy BFF Worker (Cloudflare)

```bash
cd workers/axl-bff
npm install

# Встанови secrets (один раз, або через Cloudflare Dashboard):
wrangler secret put GITHUB_TOKEN          # твій GitHub PAT (repo read + actions write)
wrangler secret put WEBHOOK_SECRET        # 32+ chars random string
wrangler secret put ANTHROPIC_API_KEY     # для Forge
wrangler secret put OPENAI_API_KEY        # для Forge (опційно)

# Wrangler vars (через wrangler.toml або dashboard):
# ALLOWED_ORIGINS=https://<твій-vercel-домен>
# GITHUB_OWNER=<твій-github-username>
# GITHUB_REPO=<назва-репо>
# GITHUB_VR_BRANCH=vr-state
# GITHUB_VR_PATH=ad2026_state/vr/latest.json

wrangler deploy --env production

# Smoke test:
curl -s https://axl-bff.<твій-subdomain>.workers.dev/healthz
# → {"ok":true,"ts":"...","version":"...","repo":"owner/repo"}
```

---

## Step 2 — Configure Vercel

```bash
# В Vercel Dashboard → Project → Settings → Environment Variables:
VITE_AXL_API_BASE = https://axl-bff.<твій-subdomain>.workers.dev
VITE_AXL_API_KEY  = <те саме значення що WORKER_API_KEY в Worker>

# Якщо деплоїш через CLI:
vercel env add VITE_AXL_API_BASE production
vercel env add VITE_AXL_API_KEY production
```

---

## Step 3 — Deploy Frontend (Vercel)

```bash
# Метод А — через Git push (рекомендовано):
git add . && git commit -m "chore: promote to PRODUCTION_SPEC_V2.1"
git push origin main
# Vercel автоматично підхоплює і будує

# Метод Б — пряме завантаження dist/:
vercel --prod
# Vercel використовує buildCommand: "npm run build" з vercel.json

# Smoke test після деплою:
curl -s https://<твій-vercel-домен>/
# → HTTP 200, SPA HTML
```

---

## Step 4 — Register GitHub Webhook

```
Repo → Settings → Webhooks → Add webhook
  Payload URL: https://axl-bff.<subdomain>.workers.dev/webhook/github
  Content type: application/json
  Secret: <значення WEBHOOK_SECRET>
  Events: Workflow runs
```

---

## Step 5 — Post-deploy smoke tests

```bash
WORKER=https://axl-bff.<subdomain>.workers.dev
UI=https://<vercel-domain>

# 1. Worker health
curl -s $WORKER/healthz | python3 -m json.tool

# 2. VR fetch (cache MISS → MISS, потім HIT)
curl -sv $WORKER/vr 2>&1 | grep "X-AXL-Cache"

# 3. Deny-by-default proxy test (має повернути 403)
curl -s $WORKER/gh/user | python3 -m json.tool

# 4. UI load
curl -s $UI/ | grep -c "<!DOCTYPE"

# 5. Gate check (фінальна верифікація)
python3 engine/scripts/check_prod_spec_gates.py \
  --ac artifacts/AC_VERSION.json \
  --pb-dir ad2026_state/pb/ \
  --ssdf artifacts/SSDF.map \
  --out /dev/null
```

---

## Artifact integrity reference

| Artifact | SHA256 (перші 16) |
|----------|-------------------|
| AC.package | `5b06f3f574cd1c01...` |
| AC.signature.jws | `2a4430f6bfc6e7fc...` |
| ARB.decision.memo | decision=APPROVED, approved_at=2026-02-25T23:56:33Z |

---

## Rollback

```bash
# UI: через Vercel Dashboard → Deployments → попередній deployment → Promote
# Worker:
wrangler rollback --env production
# Verify:
curl $WORKER/healthz
```

Повна процедура: `artifacts/rollback.plan`

---

## Incident response

Severity | Trigger | Action
---------|---------|-------
SEV-1 | Worker/UI down | rollback.plan Step 1+2
SEV-2 | Rate limit / stale data | KV invalidation via webhook
SEV-3 | Gate regression | `python3 check_prod_spec_gates.py` → investigate

Деталі: `artifacts/incident_playbook.md`
