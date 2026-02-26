# Threat Model — AXL-UI + BFF Architecture

## Trust boundaries

```
Browser (untrusted)
  │
  │  HTTPS, CORS-restricted
  ▼
Cloudflare Worker / axl-bff   ← trust boundary
  │
  │  HTTPS + server-side auth (GITHUB_TOKEN never leaves Worker)
  ▼
GitHub API
  │
  │  GITHUB_TOKEN (write) — inside Actions only
  ▼
GitHub Actions (vr-state branch commit)
```

## Secrets

| Secret | Location | Exposure risk | Mitigation |
|--------|----------|---------------|------------|
| `GITHUB_TOKEN` | Cloudflare Worker secret | Medium: if Worker compromised | Minimal scopes; rotate on incident |
| `WEBHOOK_SECRET` | Cloudflare Worker secret + GitHub Webhook | Low | HMAC-SHA-256 verification; reject missing/invalid sig |
| `GITHUB_TOKEN` (actions) | GitHub Actions secret | Low: Actions sandbox | Minimal permissions block; no exposure to UI |
| `VITE_AXL_API_BASE` | Public env var | None — it's a URL, not a secret | N/A |

## Attack vectors and controls

### 1. Token theft via browser
**Vector**: Browser receives GitHub token, XSS exfiltrates it.
**Control**: Token is a Cloudflare Worker secret — never sent to browser. Worker returns data, not tokens. `X-AXL-Api-Key` header (optional API key) is the only auth surface between UI and Worker.
**Residual risk**: None for GitHub token.

### 2. Webhook spoofing
**Vector**: Attacker sends fake webhook to invalidate KV or inject data.
**Control**: `X-Hub-Signature-256` HMAC verified with constant-time comparison. Missing or mismatched signature → 401. Body > 25 KB → 413.
**Residual risk**: Low. Secret compromise would require GitHub or Worker breach.

### 3. SSRF via GitHub proxy
**Vector**: Attacker crafts `/gh/<arbitrary-path>` to exfiltrate data from GitHub API using the Worker's token.
**Control**: Deny-by-default allowlist. Only paths under `/repos/{owner}/{repo}/*` are proxied. Exact match enforced — not a wildcard substring.
**Residual risk**: Low. Attacker limited to repo's own data, which they likely have public read access to anyway.

### 4. CORS bypass
**Vector**: Malicious site calls Worker API using victim's browser session.
**Control**: `ALLOWED_ORIGINS` enforced in CORS headers. Non-matching origins receive no CORS headers → browser blocks the response. OPTIONS preflight also enforced.
**Residual risk**: CORS is browser-enforced; server-side tools (curl) can still call Worker. Worker has no user-scoped auth — all users see the same repo data (by design).

### 5. VR.json tampering
**Vector**: Attacker commits malicious VR.json to `vr-state` branch.
**Control**: Branch requires pushes via Actions `GITHUB_TOKEN` (write). Worker reads with read-only PAT. Direct push to `vr-state` blocked by branch protection (configure separately).
**Recommendation**: Enable branch protection on `vr-state` with `Restrict who can push`.

### 6. Log injection / secret leakage in logs
**Vector**: Payload content logged, accidentally captures secrets.
**Control**: Webhook handler logs only: event type, repo name, ref. No body content logged. Secrets never logged in any path.

## Permissions matrix

| Component | Permission | Justification |
|-----------|-----------|---------------|
| Worker PAT | `contents:read`, `actions:read`, `metadata:read` | Read files and run status |
| Worker PAT | `contents:write` (optional) | Only if Worker needs to trigger dispatch; dispatch needs `repo` scope on classic PAT |
| Actions `GITHUB_TOKEN` | `contents:write` | Push VR.json to `vr-state` branch |
| Actions `GITHUB_TOKEN` | `actions:read` | Read workflow run data |

## Recommendations (post-MVP)

1. Enable `vr-state` branch protection: only `github-actions[bot]` can push
2. Add `X-AXL-Api-Key` Worker auth for UI → BFF calls (generate random key, set in Worker secret + Vercel env)
3. Rotate `GITHUB_TOKEN` quarterly
4. Enable Cloudflare Access (Zero Trust) on Worker URL for admin endpoints
5. Add rate limiting on `/dispatch/run-engine` (Cloudflare Workers Rate Limiting — free tier: 1 rule)
