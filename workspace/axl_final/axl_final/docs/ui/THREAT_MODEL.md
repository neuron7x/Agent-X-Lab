# AXL-UI — Frontend Threat Model
Protocol: AFL-2026.02 · Phase 10 · D7

## Attack Surface

### Browser-facing
| Surface | Threat | Mitigation |
|---|---|---|
| React rendering | XSS via untrusted content | All log/evidence text rendered as plain text (no dangerouslySetInnerHTML) |
| CSP | Script injection | Content-Security-Policy in vercel.json headers |
| Forge streaming | Malicious SSE payload | JSON.parse in try/catch; onToken receives plain string |
| API responses | Data injection | Zod schema validation on every response (parseResponse) |
| URL parameters | Open redirect | React Router — no arbitrary URL redirects |

### Network
| Surface | Threat | Mitigation |
|---|---|---|
| BFF calls | Auth bypass | X-AXL-Api-Key header required; Worker rejects without it |
| Dispatch | Unauthenticated engine trigger | requireApiKey + rateLimit in Worker |
| /ai/forge | Model cost abuse | Worker-side rate limit (20 req/60s/IP) + API key |

### Credentials
| Asset | Risk | Mitigation |
|---|---|---|
| OPENAI_API_KEY | Exposure in browser | Lives ONLY in Cloudflare Worker secrets — never in VITE_ env |
| ANTHROPIC_API_KEY | Exposure in browser | Same — Worker-side only |
| VITE_AXL_API_KEY | Exposed in JS bundle | Acceptable: it's the UI-to-BFF auth token, not a model key; rotate quarterly |
| VITE_SENTRY_DSN | Semi-public | DSN is low-risk; never log user PII in Sentry events |

## CSP Policy
```
default-src 'self';
script-src 'self' 'unsafe-inline';        ← required for Vite dev
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
connect-src 'self' https://*.workers.dev http://localhost:8787;
```
**When stable on prod domain:** narrow `connect-src` to exact Worker URL.

## Auth Assumptions
- UI relies on BFF (Cloudflare Worker) for all auth enforcement
- Worker validates `X-AXL-Api-Key` for protected endpoints
- No client-side JWT or session stored — stateless per-request auth
- Cloudflare Access can optionally wrap the Worker for stronger user-level auth

## XSS Mitigations
1. React escapes JSX by default
2. No `dangerouslySetInnerHTML` usage in production code
3. Evidence/log text: always `<pre>` or `<span>` with plain string content
4. External URLs: not rendered as `<a href>` without explicit allowlist

## Dependency Risk
- Regular `npm audit` in ui-verify.yml
- Dependabot configured in engine (extend to UI if needed)
- Sentry, Radix, TanStack: well-maintained, widely audited

## Known Accepted Risks
- `script-src: unsafe-inline` — required for Vite HMR; acceptable in dev; in production Vite builds without inline scripts but vercel.json is shared
- `VITE_AXL_API_KEY` in browser bundle — rotated quarterly, mitigated by Worker-side rate limiting

