# 07 Troubleshooting {#troubleshooting}

## 7.1 E2E fails: missing landmarks {#missing-landmarks}
Symptoms: assertions for `getByRole('main')` or `getByRole('navigation')` fail.
EVIDENCE: e2e/smoke.spec.ts:L93-L103
Likely cause: shell landmark contract regressed.
EVIDENCE: src/components/shell/AppShell.tsx:L73-L77
EVIDENCE: src/components/shell/AppShell.tsx:L103-L105
Verify: run `npm run test:e2e`, inspect `playwright-report/`.
EVIDENCE: playwright.config.ts:L12-L13

## 7.2 Command palette not found {#palette-not-found}
Symptoms: dialog role/label or Escape behavior assertions fail.
EVIDENCE: src/components/shell/CommandPalette.test.tsx:L24-L40
EVIDENCE: e2e/smoke.spec.ts:L54-L67
Likely cause: shortcut handler or dialog attributes changed.
EVIDENCE: src/components/shell/AppShell.tsx:L35-L43
EVIDENCE: src/components/shell/CommandPalette.tsx:L72-L77

## 7.3 Forge smoke missing providers {#forge-providers-missing}
Symptoms: E2E cannot find provider button labels.
EVIDENCE: e2e/smoke.spec.ts:L75-L78
Likely cause: provider labels changed in Forge screen.
EVIDENCE: src/components/axl/ForgeScreen.tsx:L27-L47

## 7.4 Typecheck/lint failures after refactor {#lint-typecheck-fail}
Verify with strict commands used by CI.
EVIDENCE: .github/workflows/ui-verify.yml:L32-L37
Use local commands: `npm run lint` and `npm run typecheck`.
EVIDENCE: package.json:L9-L14

## 7.5 E2E blocked before tests (Chromium missing) {#e2e-preflight-block}
Preflight script exits with install instructions when local browser is absent.
EVIDENCE: scripts/e2e-preflight.mjs:L12-L19
