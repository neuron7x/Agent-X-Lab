# AgentX Lab

![CI badge](https://img.shields.io/badge/CI-GitHub_Actions-blue)

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

## Quickstart

```bash
export PYTHONHASHSEED=0
make setup
make verify
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
