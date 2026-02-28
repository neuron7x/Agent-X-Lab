# 06 CI and Release {#ci-release}

## CI entrypoint

- `CI Supercheck` (`.github/workflows/ci-supercheck.yml`) is the branch-protection aggregator check.
- It polls GitHub check-runs for the current commit and fails closed until all required dependent checks exist and succeed.

## Dependent checks selected by CI Supercheck rules

- UI surface changes: `Lint + Typecheck + Unit Tests + Build`, `Worker TypeScript`, `Playwright E2E Smoke`, `Bundle Size Check`, `Lighthouse CI`.
- Engine/prod-spec changes: `Schema Validation (G0/G3)`, `Full RRD Gate Check`.
- Workflow/action changes: `Workflow Static Hygiene`, `Action Pin Verify`.
- Non-docs changes: `analyze`, `review`, `scan` (security checks from CodeQL/Dependency Review/Secret Scan).

## Operational note

Branch protection should require `CI Supercheck` only; other checks are enforced transitively by the aggregator logic.
