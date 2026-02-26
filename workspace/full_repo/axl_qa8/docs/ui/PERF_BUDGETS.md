# AXL-UI — Performance Budgets
Protocol: AFL-2026.02 · Phase 6 + 10 · D7

## Bundle Budgets
| Chunk | Raw size limit | Gzip estimate | Notes |
|---|---|---|---|
| Initial JS (index-*.js) | < 800KB raw | < 220KB gzip | Split into vendor-react + vendor-router + vendor-query + app |
| Route chunks | < 650KB raw | < 180KB gzip | Per lazy route module |
| vendor-radix | unrestricted | — | Large but loaded once |
| vendor-sentry | < 200KB raw | — | Only loaded when DSN present |

## Lighthouse Thresholds
| Metric | Threshold | Mode |
|---|---|---|
| Performance score | ≥ 0.80 | warn |
| Accessibility score | ≥ 0.90 | error (blocks merge) |
| Best Practices | ≥ 0.80 | warn |
| FCP | < 2000ms | warn |
| TBT | < 300ms | warn |
| TTI | < 3500ms | warn |
| CLS | < 0.10 | warn |
| LCP | < 2500ms | warn |

## Code Splitting Strategy
vite.config.ts `manualChunks`:
- `vendor-react` — react, react-dom
- `vendor-router` — react-router-dom
- `vendor-query` — @tanstack/react-query
- `vendor-radix` — @radix-ui/*
- `vendor-zod` — zod
- `vendor-sentry` — @sentry/react (dynamic import)
- `vendor-cmdk` — cmdk
- Route chunks — each module/* lazy loaded

## Updating Budgets
1. Run `npm run bundle:report` → inspect `dist/EVD-UI-BUNDLE.html` treemap
2. Identify oversized chunks
3. Apply lazy import or move to dynamic import
4. Update thresholds in `.lighthouserc.json` if justified
5. Document rationale in this file + CHANGELOG

## Prefetch Strategy
- Route chunks prefetched on nav link hover/focus (implement via `<link rel="prefetch">` or router loader)
- Sentry loaded only when `VITE_SENTRY_DSN` is set
- Large vendor chunks (radix) cached by browser after first load

## Virtualization Targets
- Evidence feed (> 100 items): react-virtual or custom windowing
- Arsenal list (> 50 items): same
- Target: scroll performance ≥ 60fps on mid-range device

