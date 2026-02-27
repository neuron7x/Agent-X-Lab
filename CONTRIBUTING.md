# Contributing

## Required reading
- `docs/00_SYSTEM_OVERVIEW.md`
- `docs/04_TEST_STRATEGY.md`
- `docs/98_CONTRACT_INDEX.md`
- `docs/99_CHECKLIST.md`

## Non-negotiables for docs changes
- Critical claims MUST include `EVIDENCE: path:Lx-Ly` anchors.
- Contracts MUST include both `Implemented at` and `Tested by` anchors.
- No behavior-changing edits are allowed in documentation-only changes.

## Local validation order
1. `node --version`
2. `npm --version`
3. `npm ci`
4. `npm run lint`
5. `npm run typecheck`
6. `npm test`
7. `npm run build`
8. `npm run test:e2e`
