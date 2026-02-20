# AgentX Lab

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

## Quickstart

```bash
python -m pip install -r requirements.lock
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
mypy .
python -m pytest -q -W error
python scripts/validate_arsenal.py --repo-root . --strict
python scripts/run_object_evals.py --repo-root .
python tools/verify_protocol_consistency.py --protocol protocol.yaml
python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json
python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json
python tools/generate_titan9_proof.py --repo-root .
```

## Repository outputs

- `VR.json`
- `artifacts/evidence/<YYYYMMDD>/<work-id>/...`
- `artifacts/release/*.zip`
- `artifacts/titan9/inventory.json`
- `artifacts/titan9/readme_commands.json`
- `artifacts/titan9/proof.log`
- `artifacts/titan9/hashes.json`

## CI

CI runs formatting, linting, typing, tests, validation/eval, and README contract checks from `.github/workflows/ci.yml`.

## Deterministic error codes

See [docs/ERRORS.md](docs/ERRORS.md) for SSOT user-facing deterministic error identifiers.

## Protocol mapping and governance

- Human-readable protocol spec: [docs/SPEC.md](docs/SPEC.md)
- Machine-checkable mapping: `protocol.yaml`

## Optional SG CLI usage

```bash
sg --config configs/sg.config.json validate-catalog
sg --config configs/sg.config.json vr
sg --config configs/sg.config.json release
```

## License

MIT (see LICENSE).
