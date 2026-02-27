# 98 Contract Index {#contract-index}

## C-ROUTE-001
MUST: App routes `/`, `/pipeline`, `/evidence`, `/arsenal`, `/forge`, `/settings`, and wildcard `*` MUST be reachable via router.
Implemented at: src/App.tsx:L48-L56
Tested by: e2e/smoke.spec.ts:L35-L52; src/modules/routes.test.tsx:L49-L73
Failure signature: route navigation test failures or missing 404 heading in smoke run.
How to reproduce:
- `npm test`
- `npm run test:e2e`

## C-A11Y-001
MUST: Shell MUST expose skip link + `navigation` + `main` landmarks.
Implemented at: src/components/shell/AppShell.tsx:L48-L53; src/components/shell/AppShell.tsx:L73-L77; src/components/shell/AppShell.tsx:L103-L105
Tested by: src/modules/routes.test.tsx:L75-L91; e2e/smoke.spec.ts:L69-L73; e2e/smoke.spec.ts:L93-L103
Failure signature: "main landmark missing" failures and accessibility regressions.
How to reproduce:
- `npm test`
- `npm run test:e2e`

## C-CMD-001
MUST: Command palette MUST be labeled dialog and close on Escape/backdrop.
Implemented at: src/components/shell/CommandPalette.tsx:L72-L77; src/components/shell/CommandPalette.tsx:L31-L37
Tested by: src/components/shell/CommandPalette.test.tsx:L30-L48; e2e/smoke.spec.ts:L54-L67
Failure signature: dialog role assertion failures or palette not closing.
How to reproduce:
- `npm test`
- `npm run test:e2e`

## C-DEMO-001
MUST: Demo mode MUST short-circuit live polling and serve mock payloads.
Implemented at: src/state/AppStateProvider.tsx:L33-L36; src/hooks/useGitHubAPI.ts:L50-L57; src/hooks/useGitHubAPI.ts:L134-L146; src/hooks/useArsenal.ts:L15-L21
Tested by: e2e/smoke.spec.ts:L80-L89
Failure signature: demo screen crashes or network-dependent regressions in offline/local smoke.
How to reproduce:
- `npm run test:e2e`

## C-API-001
MUST: Browser API boundary MUST go through BFF client module.
Implemented at: src/lib/api.ts:L1-L7; src/lib/github.ts:L1-L10
Tested by: src/lib/api.forge.test.ts:L58-L90; src/lib/api.dispatch.test.ts:L22-L29
Failure signature: API endpoint mismatch assertions fail; dispatch header missing.
How to reproduce:
- `npm test`

## C-AUTH-001
MUST: Protected actions MUST be ALLOWED/DEV_BYPASS/BLOCKED per API-key/dev rules.
Implemented at: src/components/axl/ProtectedAction.tsx:L33-L42; src/components/axl/ProtectedAction.tsx:L51-L62
Tested by: src/test/filters.test.ts:L154-L176
Failure signature: gate status tests fail; protected actions wrongly blocked/allowed.
How to reproduce:
- `npm test`

## C-EVD-001
MUST: Evidence parser MUST map statuses deterministically, count malformed lines, and cap entries.
Implemented at: src/lib/api.ts:L229-L263
Tested by: src/test/example.test.ts:L78-L123
Failure signature: parsing-related unit tests fail with status/count mismatches.
How to reproduce:
- `npm test`

## C-CI-001
MUST: CI E2E job MUST install browsers before running smoke tests and publish artifacts.
Implemented at: .github/workflows/ui-e2e.yml:L30-L58
Tested by: build_proof/docs_audit/outputs/08_test_e2e.txt:L1-L8 (local preflight failure mode proves dependency)
Failure signature: preflight/browser missing errors or absent trace artifacts in CI failures.
How to reproduce:
- `npm run test:e2e`
