# TECHNICAL DEBT REPORT — 2026-02-26

## CI blockers observed

1. **Root install determinism break**: `npm ci` failed when lockfile drifted from `package.json`.
2. **Worker dependency resolution break**: `workers/axl-bff` had an `ERESOLVE` peer dependency conflict between `wrangler` and `@cloudflare/workers-types`.
3. **Lint scope contamination**: root lint ran as `eslint .` and scanned archive/snapshot folders, generating non-product warnings.
4. **Node 20 compatibility risk**: `rollup-plugin-visualizer@^7` may require Node versions beyond the CI baseline and should be monitored or pinned with lockfile regeneration when network policy allows.

## Remediation status

- Root lint scope constrained to active source and archive-like directories ignored in flat config.
- Worker TypeScript gate unmasked in CI (`npx tsc --noEmit` without filtering).
- Worker lockfile and root lockfile must remain synchronized with `npm ci`.
- `rollup-plugin-visualizer` remains `^7.0.0` to preserve lockfile determinism in this branch; pinning requires lockfile regeneration in an environment with registry access.
