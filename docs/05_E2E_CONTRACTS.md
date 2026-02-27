# 05 E2E Contracts {#e2e-contracts}

## 5.1 Contract set {#e2e-contract-set}
- App load contract: page reaches visible `main` and no uncaught page errors.
EVIDENCE: e2e/smoke.spec.ts:L9-L16
- Navigation contract: bottom nav visible with route links accessible.
EVIDENCE: e2e/smoke.spec.ts:L18-L33
- Routing contract: `/pipeline`, `/evidence`, `/forge`, `/settings`, and 404 fallback.
EVIDENCE: e2e/smoke.spec.ts:L35-L52
- Command palette contract: open Ctrl+K, close Escape, labeled dialog.
EVIDENCE: e2e/smoke.spec.ts:L54-L67
- Landmark contract: all primary routes expose `main`; root has `navigation`.
EVIDENCE: e2e/smoke.spec.ts:L92-L103

## 5.2 Failure artifacts and trace paths {#e2e-artifacts}
- Local report outputs configured in Playwright config.
EVIDENCE: playwright.config.ts:L9-L13
- Trace is generated on first retry and screenshots on failure.
EVIDENCE: playwright.config.ts:L16-L18
- CI uploads trace/report artifact on failure and JSON evidence always.
EVIDENCE: .github/workflows/ui-e2e.yml:L44-L58
