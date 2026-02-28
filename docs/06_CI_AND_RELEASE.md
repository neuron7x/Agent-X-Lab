# 06 CI and Release {#ci-release}

## 6.1 Script inventory {#script-inventory}
Documented from `package.json` scripts section: dev/build/lint/typecheck/test/test:e2e/a11y/bundle/perf utilities.
EVIDENCE: package.json:L6-L29

## 6.2 Local gate order (canonical) {#local-gates}
1. `node --version`
2. `npm --version`
3. `npm ci`
4. `npm run lint`
5. `npm run typecheck`
6. `npm test`
7. `npm run build`
8. `npm run test:e2e`
Evidence logs are committed under `build_proof/docs_audit/outputs/`.
EVIDENCE: build_proof/docs_audit/commands.txt:L1-L16

## 6.3 CI workflow behavior map {#workflow-map}
- `ui-verify.yml`: lint/typecheck/unit/a11y/build/bundle checks; uploads build and a11y artifacts.
EVIDENCE: .github/workflows/ui-verify.yml:L14-L72
- `ui-e2e.yml`: installs browsers in CI, runs e2e, uploads traces on failure + JSON evidence always.
EVIDENCE: .github/workflows/ui-e2e.yml:L27-L58
- `ui-perf.yml`: bundle budget and lighthouse jobs with artifact upload.
EVIDENCE: .github/workflows/ui-perf.yml:L14-L77

## 6.4 Artifact locations {#artifact-locations}
- Unit/a11y JSON: `dist/EVD-UI-TESTS.json` and `dist/EVD-UI-A11Y.json`.
EVIDENCE: vitest.config.ts:L31-L32
EVIDENCE: .github/workflows/ui-verify.yml:L46-L53
- E2E JSON + HTML report: `dist/EVD-UI-E2E.json`, `playwright-report/`.
EVIDENCE: playwright.config.ts:L11-L13
EVIDENCE: .github/workflows/ui-e2e.yml:L44-L58


## 6.5 Security/quality gate hardening {#security-gates-hardening}
Security-gate policy, correctness, and low-noise defaults are documented in `docs/08_SECURITY_GATES.md`.
EVIDENCE: docs/08_SECURITY_GATES.md:L1-L33
