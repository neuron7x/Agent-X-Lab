# AgentX Lab

![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A deterministic cognitive-agent architecture with mechanized validation for shipping
prompt catalogs and proof bundles as a GitHub-ready project.

Built on the principle: **quality emerges from structured verification, not assumption.**
Every output is evidence-bound, every gate is fail-closed, every artifact is reproducible.

## Quickstart

```bash
make setup
make check
make proof
```

Or run the scripted flow with `./scripts/quickstart.sh`.

## What This Is

AgentX Lab is an independent research and engineering platform for building, validating,
and shipping cognitive-agent catalogs with production-grade governance.

The system enforces:
- **Determinism** — `PYTHONHASHSEED=0` across all tooling; outputs are reproducible
- **Fail-closed gates** — ambiguity is an error, not a warning
- **Evidence discipline** — every validation emits auditable artifacts
- **Protocol consistency** — `protocol.yaml` is machine-validated against all tooling

## Repository outputs

- `VR.json` — verification record with status, metrics, and blockers
- `artifacts/evidence/<YYYYMMDD>/<work-id>/` — auditable run evidence
- `artifacts/release/*.zip` — shippable release bundle
- `artifacts/titan9/inventory.json` — full repo inventory
- `artifacts/titan9/readme_commands.json` — contract-verified commands
- `artifacts/titan9/proof.log` — deterministic proof log
- `artifacts/titan9/hashes.json` — file hash registry

## Quality Gate Pipeline

`make check` runs the full gate sequence:

| Gate | Tool | Purpose |
|------|------|---------|
| Format | `ruff format --check` | Zero formatting drift |
| Lint | `ruff check` | Zero lint violations |
| Types | `mypy` | Full static type coverage |
| Tests | `pytest -W error` | Zero failures, warnings as errors |
| Arsenal | `validate_arsenal.py` | Catalog integrity |
| Evals | `run_object_evals.py` | Agent evaluation harnesses |
| Protocol | `verify_protocol_consistency.py` | Spec ↔ code alignment |
| Inventory | `titan9_inventory.py` | Repo inventory generation |
| README contract | `verify_readme_contract.py` | Quickstart SSOT enforcement |
| Workflow hygiene | `verify_workflow_hygiene.py` | CI file structure |
| Action pinning | `verify_action_pinning.py` | SHA-pinned GitHub Actions |
| Secret scan | `secret_scan_gate.py` | No secrets in tracked files |

## Security

Security PR checks in `.github/workflows/security.yml` run a full lockfile vulnerability
audit via `make vuln-scan` (`pip-audit`), writing `artifacts/security/pip-audit.json`.
Temporary ignores must be listed in `policies/pip_audit_allowlist.json` with an expiry date.

Use `make check_r8` to run the standard checks plus workflow hygiene/action pinning/readme-contract
verification and emit `artifacts/feg_r8/gates.jsonl`.

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

If any required field is missing, treat the run as fail-closed (`E_INPUT_AMBIGUITY`) and avoid
making repository changes.

## Protocol mapping and governance

- Human-readable protocol spec: [docs/SPEC.md](docs/SPEC.md)
- Architecture overview: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Merge gates reference: [docs/merge-gates.md](docs/merge-gates.md)
- Machine-checkable mapping: `protocol.yaml`

## CLI usage

```bash
sg --config configs/sg.config.json validate-catalog
sg --config configs/sg.config.json vr
sg --config configs/sg.config.json release
```

## License

MIT
