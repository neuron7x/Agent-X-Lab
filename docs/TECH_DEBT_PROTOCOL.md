# TECHNICAL DEBT PROTOCOL (Canonical)

## Purpose
This document is the single source of truth for technical debt control across Security, Lint, CI, and Evidence artifacts.

## Protocol Domains

### 1) Security
- Enforce no-secrets policy in tracked files.
- Record secret-scan findings in machine-readable evidence.
- Treat secret findings as blocking for follow-up PRs.

### 2) Dependency
- Dependency installation and updates must be explicit and reproducible.
- Offline-constrained runs must be marked as blocked with reasons.

### 3) Lint
- Lint status must be measured and serialized per PR.
- No silent pass by skipping failures.

### 4) ESLint
- Keep ESLint execution as an explicit gate command.
- Preserve exit code and command log in evidence.

### 5) Repository Hygiene
- No secrets in repo.
- No large tracked binaries beyond policy threshold.
- No archive artifacts in lint/test scopes.

### 6) Retention
- Baseline evidence is immutable per PR and comparable between PRs.
- Store command logs and structured JSON under `evidence/`.

### 7) CI Determinism
- Use deterministic environment defaults: `PYTHONHASHSEED=0`, `LC_ALL=C`, `LANG=C`, `TZ=UTC`, `GIT_PAGER=cat`, `PAGER=cat`, `PYTHONDONTWRITEBYTECODE=1`.
- Stable sorting for scans and listings.

### 8) Tests
- Unit tests and coverage must be measured, not inferred.
- Failing tests are recorded, not auto-fixed in TD-0.

### 9) Documentation
- CI gates, threat model, and hygiene policy must remain synchronized.
- Any protocol change must update docs and baseline tooling together.

### 10) Final Verification
- Run baseline collector script.
- Preserve all exit codes.
- Emit comparable evidence artifacts.

## Execution model: atomic PRs
Technical debt remediation is decomposed into atomic PRs:
1. One epic per PR.
2. Each PR has minimal bounded scope.
3. Each PR must include reproducible evidence.
4. No mixed concerns (e.g., lint fixes and security refactors in one PR).
5. Merge only after gates/evidence are explicit.
