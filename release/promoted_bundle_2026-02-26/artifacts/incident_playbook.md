# AXL — Incident Playbook (Ops)

**Spec**: PRODUCTION_SPEC_V2.1  
**Principle**: Fail-closed. Preserve evidence chain. Minimal blast radius.

## Severity definitions

- **SEV0**: Active data exposure, token compromise, integrity failure of signed artifacts.
- **SEV1**: Production outage >10 min or widespread functional regression.
- **SEV2**: Partial outage, degraded performance, rate-limit misbehavior.
- **SEV3**: Minor bug, cosmetic, isolated user impact.

## Immediate actions (first 5 minutes)

1) **Freeze autonomy / release**: stop deploys; disable dispatch endpoints if needed.
2) **Preserve evidence**:
   - Export Worker logs (time window)
   - Save current `VR.json` and PB bundles
   - Record the exact deployed versions (Worker + Vercel)
3) **Containment**:
   - Rotate `GITHUB_TOKEN` if suspicious
   - Rotate `AXL_API_KEY` if abused
   - Disable webhook temporarily if it is the attack vector

## Common incident playbooks

### A) Unauthorized access / key leakage suspicion

- Rotate secrets in this order: `GITHUB_TOKEN` → `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` → `AXL_API_KEY` → `WEBHOOK_SECRET`.
- Invalidate KV cache (`KV_INDEX_KEY` prefix invalidation) if it might contain sensitive data.
- Audit repository history for accidental secret commits.

### B) Worker outage / 5xx surge

- Check Cloudflare status + Worker logs.
- Verify KV availability (rate limiter fails open by design; still capture evidence).
- Roll back Worker to last known good version.

### C) UI outage

- Confirm Worker health (`/healthz`).
- Confirm Vercel env vars are correct (especially `VITE_AXL_API_BASE`).
- Roll back Vercel deploy.

### D) Evidence chain integrity failure

- Treat as **SEV0**.
- Stop all automation.
- Run chain audit: PB hash chain validation + AC signature verification.
- Restore QA7 baseline if integrity cannot be re-established.

## Communication template

- What happened (facts only)
- When it started (UTC)
- Blast radius (who/what affected)
- Mitigation steps taken
- Next updates cadence

## Post-incident requirements

- Root cause analysis with evidence pointers.
- Corrective actions mapped to gates/controls.
- Add regression tests + CI gates.
