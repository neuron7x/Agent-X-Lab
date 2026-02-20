# AgentX Lab

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

## Quickstart

`PYTHONHASHSEED=0` is required for all local and CI execution surfaces.

```bash
make setup
make test
make proof
```

### Expanded command mapping (Makefile SSOT)

```bash
# make setup
python -m pip install -r requirements.lock
python -m pip install -r requirements-dev.txt

# make test
python -m pytest -q -W error

# make proof
python tools/generate_titan9_proof.py --repo-root .
```

## Codespaces

Open this repository in GitHub Codespaces and run `make test`.

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

## Optional SG CLI usage

```bash
sg --config configs/sg.config.json validate-catalog
sg --config configs/sg.config.json vr
sg --config configs/sg.config.json release
```

## License

MIT (see LICENSE).
