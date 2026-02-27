# 04 Test Strategy {#test-strategy}

## 4.1 Test frameworks and configuration {#frameworks-config}
- Vitest config: jsdom, setup file, include/exclude, JSON reporter output path.
EVIDENCE: vitest.config.ts:L7-L33
- Playwright config: smoke test dir, report outputs, trace/screenshot policy.
EVIDENCE: playwright.config.ts:L4-L18

## 4.2 Test Map {#test-map}
| Test file | Behavior/contract | Key assertions | Artifacts on failure |
|---|---|---|---|
| `src/modules/routes.test.tsx` | Shell landmarks + route container mounting | nav/main + skip-link selector; route placeholder render | Vitest JSON report (`dist/EVD-UI-TESTS.json`) |
| `src/components/shell/CommandPalette.test.tsx` | Command palette a11y + close behaviors | dialog role/label, Escape, backdrop close | Vitest JSON report |
| `src/test/a11y.test.tsx` | Axe/WCAG checks on key components | no critical violations; textbox/button/dialog assertions | Vitest JSON report |
| `src/test/example.test.ts` | Deterministic gate mapping + evidence parsing | status taxonomy, elapsed format, parse failure counting | Vitest JSON report |
| `src/test/filters.test.ts` | Evidence filtering + gate status policy | PASS/FAIL/UNKNOWN filters, action gate statuses | Vitest JSON report |
| `src/lib/api.forge.test.ts` | Forge endpoint routing + API error taxonomy | endpoint selection; 401/429/schema failures | Vitest JSON report |
| `src/lib/api.dispatch.test.ts` | Dispatch API key header contract | `X-AXL-Api-Key` propagated | Vitest JSON report |
| `e2e/smoke.spec.ts` | Route, a11y landmarks, command palette, forge smoke | page load no JS crash, 404, Ctrl+K/Escape, landmarks | Playwright report (`playwright-report/`), JSON (`dist/EVD-UI-E2E.json`) |

Evidence for rows above:
EVIDENCE: src/modules/routes.test.tsx:L75-L91
EVIDENCE: src/components/shell/CommandPalette.test.tsx:L24-L66
EVIDENCE: src/test/a11y.test.tsx:L1-L86
EVIDENCE: src/test/example.test.ts:L7-L124
EVIDENCE: src/test/filters.test.ts:L36-L176
EVIDENCE: src/lib/api.forge.test.ts:L58-L160
EVIDENCE: src/lib/api.dispatch.test.ts:L22-L29
EVIDENCE: e2e/smoke.spec.ts:L9-L105

## 4.3 Coverage limits (explicit) {#coverage-limits}
- No E2E assertion validates successful forge token stream content semantics.
EVIDENCE: e2e/smoke.spec.ts:L75-L89
- E2E preflight can fail before execution if Chromium is absent.
EVIDENCE: scripts/e2e-preflight.mjs:L8-L19
