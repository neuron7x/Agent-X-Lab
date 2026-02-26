# CI Gates

## Gate Matrix

### UI Gate
- Local command(s): `npm run lint`, `npm run typecheck`, `npm run test:unit -- --coverage`, `npm run build`
- Evidence artifacts: `evidence/TD0_COMMAND_LOG.txt`, `evidence/TD0_BASELINE.json`
- Pass/fail: pass if all listed commands exit `0`; fail otherwise.

### Worker Gate
- Local command(s): `cd workers/axl-bff && npm ci && npm run typecheck`
- Evidence artifacts: `evidence/TD0_COMMAND_LOG.txt`, `evidence/TD0_BASELINE.json`
- Pass/fail: pass if worker commands exit `0`; fail otherwise.

### Python Gate
- Local command(s): `python3 --version`, `python3 scripts/td0/scan_large_files.py`
- Evidence artifacts: `evidence/TD0_COMMAND_LOG.txt`, `evidence/TD0_BASELINE.json`
- Pass/fail: pass if commands exit `0`; fail otherwise.

### Gates Orchestrator
- Local command(s): `bash scripts/td0/baseline.sh`
- Evidence artifacts: `evidence/TD0_COMMAND_LOG.txt`, `evidence/TD0_BASELINE.json`
- Pass/fail: pass if orchestrator exits `0` and records all check exits.

### E2E Gate
- Local command(s): project-defined E2E command (to be bound in subsequent PR).
- Evidence artifacts: baseline JSON check entries once bound.
- Pass/fail: pass only with explicit command exit `0` evidence.

### Security Gate
- Local command(s): `bash scripts/td0/scan_secrets.sh`
- Evidence artifacts: `evidence/TD0_BASELINE.json` (`secrets_findings`)
- Pass/fail: pass when no findings and exit `0`; fail on findings (exit `2`).

### Dependency Review Gate
- Local command(s): install command + lockfile validation (offline constraints may block install)
- Evidence artifacts: `evidence/TD0_BASELINE.json` (`blocked` and check exits)
- Pass/fail: pass with reproducible install success; blocked if policy disallows network and deps are missing.
