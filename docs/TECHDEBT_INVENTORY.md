# Technical Debt Inventory (Full Repository)

Date (UTC): 2026-02-27  
Branch: `chore/techdebt-inventory`  
Scope: UI (`src`, root configs, CI) + worker (`workers/axl-bff`)

## Executive summary (top 5 blockers)

1. **Type-safety gates are intentionally weakened in root TS config** (`skipLibCheck: true`, `noImplicitAny: false`, `strictNullChecks: false`), allowing null and implicit-any issues to slip through.  
2. **Lint policy drift exists**: source contains multiple `eslint-disable` directives (including unused disable warnings from lint output), indicating quality guardrail erosion.  
3. **E2E is not reliably runnable locally by default** in this environment because Playwright browser binaries are missing; `npm run test:e2e` failed immediately with browser executable errors.  
4. **CI gate inconsistency/soft-fail patterns** exist in workflows (e.g., `continue-on-error` in key jobs and `|| true` in evidence generation/build scripts), reducing fail-closed confidence.  
5. **Large duplicated archive tree (`archive/workspace_wrapper/...`) inflates scan noise and maintenance load**, duplicating lint suppressions and console patterns across effectively copied UI files.

## Prioritized debt register

| ID | Severity | Area | Symptom / Risk | Proposed remediation | Files |
|---|---|---|---|---|---|
| TD-001 | P0 | TypeScript quality gates | Root config disables strictness (`noImplicitAny: false`, `strictNullChecks: false`) and skips lib checks, reducing type-safety coverage. | Move to strict baseline in staged PRs: flip `strictNullChecks` + `noImplicitAny`, then reduce/justify exceptions. | `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json` |
| TD-002 | P0 | E2E reliability | `npm run test:e2e` failed (exit 1) due to missing Playwright Chromium binary in local env, so smoke tests are not portable by default. | Add deterministic local bootstrap script/docs (`npx playwright install --with-deps chromium`) and preflight check in `test:e2e`. | `package.json`, `playwright.config.ts`, `e2e/smoke.spec.ts` |
| TD-003 | P1 | Lint hygiene | 20 lint warnings (unused disable directives + react-refresh export warnings + hook deps warning). | Remove stale `eslint-disable` comments and split component/helper exports per rule guidance. | `src/components/**`, `src/hooks/**` |
| TD-004 | P1 | CI fail-closed posture | Workflow steps use soft-fail behavior (`continue-on-error`, `|| true`) in quality/evidence paths, increasing false-green risk. | Convert soft-fail steps to hard gates where appropriate; isolate non-blocking telemetry into separate clearly-marked jobs. | `.github/workflows/*.yml`, `package.json` |
| TD-005 | P1 | Security / logging discipline | Multiple `console.warn/error` occurrences in app and worker paths can leak diagnostics and create noisy telemetry in prod contexts. | Route via centralized logger with env-based redaction and severity control. | `src/lib/observability.ts`, `src/lib/api.ts`, `workers/axl-bff/src/index.ts`, etc. |
| TD-006 | P2 | Comment debt | `TODO` present in security threat model indicates unresolved auth architecture gap. | Track with issue + owner + target milestone; replace SPA API key model with real identity flow. | `docs/security/threat-model.md` |
| TD-007 | P2 | Repository structure | Archive mirror duplicates many source patterns, polluting static scans and raising maintenance overhead. | Exclude/archive outside active tree or add explicit scan excludes and ownership rules. | `archive/workspace_wrapper/axl_final/**` |
| TD-008 | P3 | Runtime warnings | Tooling warnings (`browserslist stale DB`, npm env warning) indicate environment/config drift. | Normalize npm config and add periodic dependency metadata update job. | build/test command outputs |

## Inventory signals

### Toolchain
- `node -v` → `v22.21.1`
- `npm -v` → `11.4.2`
- `.node-version` → `20.11.1`
- `.nvmrc` → `20`

### App scripts and configs reviewed
- `package.json` scripts include core checks (`lint`, `typecheck`, `test`, `build`, `test:e2e`) and one script with `|| true` (`build:perf`).
- TS configs reviewed: `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`.
- ESLint config reviewed: `eslint.config.js`.
- Playwright config/spec reviewed: `playwright.config.ts`, `e2e/smoke.spec.ts`.

### CI workflows and gate summaries
- `.github/workflows/ui-verify.yml`: CI gate for lint + typecheck + unit tests + a11y + build + bundle budget + worker typecheck.
- `.github/workflows/ui-e2e.yml`: installs browsers and runs Playwright smoke tests; uploads traces/evidence.
- `.github/workflows/ui-perf.yml`: bundle budget enforcement and Lighthouse run (Lighthouse currently warn-only via `continue-on-error`).
- `.github/workflows/prod-spec-gates.yml`: schema + PROD_SPEC gate checks + PB chain integrity checks.
- `.github/workflows/run-engine-dispatch.yml`: dispatch/manual engine run, schema/hash checks, and VR publish workflow.

### Static scan findings (rg)
- `eslint-disable`: found in active source files and duplicated archive files.
- `@ts-ignore/@ts-expect-error`: present in UI tests (and archive duplicate).
- `TODO/FIXME`: one TODO found in threat model.
- `console.error/console.warn`: present in UI app code, tests, and worker code (plus archive duplicates).
- TS flags: `skipLibCheck` present; `noImplicitAny` disabled; `strictNullChecks` disabled in root tsconfig.

## Evidence

> Format: **command → exit code → excerpt (3–15 lines)**

### Environment and config inspection

1. **`node -v` → exit 0**
```text
v22.21.1
```

2. **`npm -v` → exit 0**
```text
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.
11.4.2
```

3. **`cat .node-version` → exit 0**
```text
20.11.1
```

4. **`cat .nvmrc` → exit 0**
```text
20
```

5. **`cat package.json` → exit 0**
```text
"scripts": {
  "lint": "eslint src",
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "test:e2e": "playwright test",
  "build:perf": "npm run build && npx lhci collect --config=.lighthouserc.json || true"
}
```

6. **`cat tsconfig.json` → exit 0**
```text
"noImplicitAny": false,
"skipLibCheck": true,
"strictNullChecks": false
```

7. **`cat tsconfig.app.json` → exit 0**
```text
"strict": true,
"skipLibCheck": true,
"noImplicitAny": false
```

8. **`cat tsconfig.node.json` → exit 0**
```text
"strict": true,
"skipLibCheck": true
```

9. **`cat eslint.config.js` → exit 0**
```text
rules: {
  ...reactHooks.configs.recommended.rules,
  "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
  "@typescript-eslint/no-unused-vars": "off",
}
```

10. **`cat playwright.config.ts` → exit 0**
```text
projects: [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
],
webServer: {
  command: 'npm run preview',
  url: 'http://localhost:4173',
}
```

11. **`cat e2e/smoke.spec.ts` → exit 0**
```text
test.describe('AXL-UI smoke tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });
```

### CI inventory

12. **`find .github/workflows -maxdepth 1 -name '*.yml' -print | sort` → exit 0**
```text
.github/workflows/prod-spec-gates.yml
.github/workflows/run-engine-dispatch.yml
.github/workflows/ui-e2e.yml
.github/workflows/ui-perf.yml
.github/workflows/ui-verify.yml
```

13. **`sed -n '1,260p' .github/workflows/ui-e2e.yml` → exit 0**
```text
- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium

- name: Run E2E tests
  run: npm run test:e2e
```

14. **`sed -n '1,280p' .github/workflows/ui-perf.yml` → exit 0**
```text
- name: Run Lighthouse CI
  run: lhci autorun --config=.lighthouserc.json
  continue-on-error: true  # warn-only for initial rollout
```

15. **`sed -n '1,220p' .github/workflows/run-engine-dispatch.yml` → exit 0**
```text
permissions:
  contents: write
  actions: read
...
python -m exoneural_governor.cli ... vr --out ad2026_state/vr/latest.json
```

16. **`sed -n '1,280p' .github/workflows/prod-spec-gates.yml` → exit 0**
```text
- name: Run PROD_SPEC gate checker
  ...
  continue-on-error: true  # We capture exit code manually
```

### Static scans

17. **`rg -n "eslint-disable" ...` → exit 0**
```text
./src/components/axl/ProtectedAction.tsx:94:      // eslint-disable-next-line no-console
./src/components/ui/command.tsx:1:/* eslint-disable @typescript-eslint/no-empty-object-type */
./src/hooks/useGitHubAPI.ts:1:/* eslint-disable react-hooks/rules-of-hooks */
./tailwind.config.ts:1:/* eslint-disable @typescript-eslint/no-require-imports */
```

18. **`rg -n "@ts-ignore|@ts-expect-error" ...` → exit 0**
```text
./src/lib/api.forge.test.ts:27:    // @ts-expect-error - partial mock
./src/lib/api.dispatch.test.ts:9:    // @ts-expect-error partial response
```

19. **`rg -n "TODO|FIXME" .` → exit 0**
```text
./docs/security/threat-model.md:79:## TODO: Replace SPA API key with real identity
```

20. **`rg -n "console\.(error|warn)" ...` → exit 0**
```text
./src/lib/observability.ts:37:    console.warn(`[AXL] ${msg}`, data ?? '');
./src/lib/observability.ts:41:    console.error(`[AXL] ${msg}`, data ?? '');
./src/pages/NotFound.tsx:8:    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
./workers/axl-bff/src/index.ts:434:    console.warn('[webhook] signature verification failed');
```

21. **`rg -n "skipLibCheck|noImplicitAny|strictNullChecks" tsconfig*.json` → exit 0**
```text
tsconfig.app.json:8:    "skipLibCheck": true,
tsconfig.app.json:22:    "noImplicitAny": false,
tsconfig.json:11:    "skipLibCheck": true,
tsconfig.json:14:    "strictNullChecks": false
```

### Verification run (fail-closed sequence)

22. **`git clean -xfd` → exit 0**
```text
Removing node_modules/
Removing workers/axl-bff/node_modules/
```

23. **`npm ci` → exit 0**
```text
npm warn deprecated whatwg-encoding@2.0.0: Use @exodus/bytes instead...
npm warn deprecated abab@2.0.6: Use your platform's native atob() and btoa() methods instead
added 667 packages in 8s
```

24. **`npm run lint` → exit 0**
```text
✖ 20 problems (0 errors, 20 warnings)
0 errors and 9 warnings potentially fixable with the `--fix` option.
```

25. **`npm run typecheck` → exit 0**
```text
> axl-ui@1.3.0-qa8 typecheck
> tsc --noEmit
```

26. **`npm test` → exit 0**
```text
Test Files  6 passed (6)
Tests  72 passed (72)
Duration  7.46s
JSON report written to /workspace/Agent-X-Lab/dist/EVD-UI-TESTS.json
```

27. **`npm run build` → exit 0**
```text
vite v5.4.19 building for production...
✓ 2019 modules transformed.
✓ built in 5.43s
```

28. **`npm run test:e2e` → exit 1 (STOP HERE by fail-closed rule)**
```text
Error: browserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/.../chrome-headless-shell
Looks like Playwright Test or Playwright was just installed or updated.
Please run the following command to download new browsers:
    npx playwright install
11 failed
```

### Not run due to fail-closed stop condition
- `bash -lc "cd workers/axl-bff && npm ci && npm run typecheck"` was **not executed** because the verification sequence stopped at first failing gate (`npm run test:e2e`).

