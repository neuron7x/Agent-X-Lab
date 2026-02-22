# AgentX Lab

![CI badge](https://img.shields.io/badge/CI-GitHub_Actions-blue)

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

## Quickstart

```bash
make setup
make check
make proof
```

Or run the scripted flow with `./scripts/quickstart.sh`.

## Repository outputs

- `VR.json`
- `artifacts/evidence/<YYYYMMDD>/<work-id>/...`
- `artifacts/release/*.zip`
- `artifacts/titan9/inventory.json`
- `artifacts/titan9/readme_commands.json`
- `artifacts/titan9/proof.log`
- `artifacts/titan9/hashes.json`

## CI

CI runs formatting, linting, typing, tests, validation/eval, protocol checks, inventory/readme contract checks, and proof generation from `.github/workflows/ci.yml`.

Security PR checks in `.github/workflows/security.yml` run a full lockfile vulnerability audit via `make vuln-scan` (`pip-audit`), writing `artifacts/security/pip-audit.json`. Temporary ignores must be listed in `policies/pip_audit_allowlist.json` with an expiry date.

Use `make check_r8` to run the standard checks plus workflow hygiene/action pinning/readme-contract verification and emit `artifacts/feg_r8/gates.jsonl`.

## Deterministic error codes

See [docs/ERRORS.md](docs/ERRORS.md) for SSOT user-facing deterministic error identifiers.

## Cleanup run input contract

For deterministic post-development cleanup runs, provide a complete cleanup spec before execution:

- `target_branch`
- `allowed_change_types`
- `disallowed_change_types`
- `gates`
- `artifacts_policy.forbidden_tracked_globs`
- `artifacts_policy.allowed_tracked_globs`
- `offline_policy`
- `output_mode`

If any required field is missing, treat the run as fail-closed (`E_INPUT_AMBIGUITY`) and avoid making repository changes.

## Protocol mapping and governance

- Human-readable protocol spec: [docs/SPEC.md](docs/SPEC.md)
- Machine-checkable mapping: `protocol.yaml`

## Optional SG CLI usage

```bash
sg --config configs/sg.config.json validate-catalog
sg --config configs/sg.config.json vr
sg --config configs/sg.config.json release
```

## Operations

Operational runbooks for incident handling and recovery:

- [Incident response](docs/runbooks/incident-response.md) — severity model, triage algorithm, and escalation path.
- [Release rollback](docs/runbooks/rollback.md) — deterministic rollback and post-rollback verification.
- [Disaster recovery](docs/runbooks/disaster-recovery.md) — RTO/RPO targets and recovery procedure.

For evidence localization during operations, start with `artifacts/titan9/proof.log` and use `python tools/generate_titan9_proof.py --repo-root . --cycles 3` to regenerate a consistent proof set under `artifacts/titan9/`.

## License

MIT (see LICENSE).
