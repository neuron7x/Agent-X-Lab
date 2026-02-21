# AgentX Lab

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

## Quickstart

```bash
make setup && make test && make proof
```

Codespaces supported.

## Repository outputs

- `VR.json`
- `artifacts/evidence/<YYYYMMDD>/<work-id>/...`
- `artifacts/release/*.zip`
- `artifacts/titan9/inventory.json`
- `artifacts/titan9/readme_commands.json`
- `artifacts/titan9/proof.log`
- `artifacts/titan9/hashes.json`

## CI

CI runs `make ci` from `.github/workflows/ci.yml`.

## Deterministic error codes

See [docs/ERRORS.md](docs/ERRORS.md) for SSOT user-facing deterministic error identifiers.

## Protocol mapping and governance

- Human-readable protocol spec: [docs/SPEC.md](docs/SPEC.md)
- Machine-checkable mapping: `protocol.yaml`
- LLM signal artifact: [docs/LLM_INTELLIGENCE_MAP.md](docs/LLM_INTELLIGENCE_MAP.md)

## Optional SG CLI usage

```bash
sg --config configs/sg.config.json validate-catalog
sg --config configs/sg.config.json vr
sg --config configs/sg.config.json release
```

## License

MIT (see LICENSE).
