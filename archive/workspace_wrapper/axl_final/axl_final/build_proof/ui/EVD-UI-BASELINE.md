# EVD-UI-BASELINE.md
Protocol: AFL-2026.02 · GATE-1 Evidence · Generated: 2026-02-25

## Environment
- Node: 20.x (.nvmrc pinned)
- Package manager: npm (package-lock.json present)
- Framework: Vite 5 + React 18 + TypeScript 5

## Commands + Results

### 1. npm ci
```
Status: PASS (0 errors, clean install)
```

### 2. npm run typecheck
```
> tsc --noEmit
Status: PASS (0 errors, 0 warnings)
```

### 3. npm run lint
```
Status: PASS (0 errors, 20 warnings — all expected react-hooks/exhaustive-deps)
Exit code: 0 (warnings do not block)
```

### 4. npm run test:unit
```
Test Files: 5 passed (5)
Tests:      71 passed (71)
Duration:   ~30s
Status: PASS
```

### 5. npm run build (VITE_AXL_API_BASE=https://placeholder.workers.dev)
```
✓ 2019 modules transformed
Built in 19.19s
Status: PASS

Bundle sizes (gzip):
  vendor-react:   67.26 kB  ✅ < 220kB budget
  index:          11.86 kB
  vendor-misc:    31.28 kB
  vendor-query:    8.00 kB
  ArsenalRoute:    4.37 kB  ✅ < 180kB chunk budget
  PipelineRoute:   2.69 kB
  ForgeRoute:      2.45 kB
  SettingsRoute:   1.69 kB
  StatusRoute:     1.72 kB
  EvidenceRoute:   1.29 kB
```

## Gate Status
| Gate | Status | Evidence |
|------|--------|----------|
| GATE-CRIT-1: Forge endpoint fix | ✅ PASS | forgeStream uses endpoint param; tests verify |
| GATE-CRIT-2: Deterministic builds | ✅ PASS | npm ci + package-lock.json + .nvmrc=20 |
| GATE-1: Baseline green | ✅ PASS | 71/71 tests, 0 TS errors, build ok |
| GATE-2: Route code-splitting | ✅ PASS | Separate chunks per route in dist/assets |
| GATE-3: Zod validation | ✅ PASS | parseResponse wraps all fetches |
| GATE-4: a11y axe checks | ✅ PASS | 0 critical violations |
| GATE-5: Auth boundary | ✅ PASS | ProtectedAction + useActionGate |
| GATE-6: Bundle budgets | ✅ PASS | All chunks under budget |
| GATE-7: Tests pyramid | ✅ PASS | unit+a11y+e2e configured |
| GATE-8: Observability | ✅ PASS | Sentry dynamic import + structured logs |
| GATE-9: CI workflows | ✅ PASS | ui-verify + ui-e2e + ui-perf |
| GATE-10: Docs | ✅ PASS | README + THREAT_MODEL + PERF_BUDGETS |
