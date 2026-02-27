# PR Series Plan

## Risk ranking

| ID | Risk | P | Impact | Detectability | Score |
|---|---|---:|---:|---:|---:|
| R1 | Python test runner coupled to missing `.venv` path | 5 | 4 | 4 | 80 |
| R2 | Missing taxonomy make targets blocks CI standardization | 4 | 4 | 3 | 48 |
| R3 | Missing proof bundle manifest regeneration | 4 | 3 | 3 | 36 |
| R4 | Setup depends on external Python index availability | 3 | 3 | 2 | 18 |

## Planned PRs (bounded)

1. **PR-1 Deterministic make wrappers + proof bundle baseline**
   - Gates targeted: G1 (partial), G2 (partial), G5 (partial), G10 (partial)
   - Files touched: `Makefile`, `pytest.ini`, `scripts/generate_manifest.py`, `artifacts/proof_bundle/*`
   - Acceptance criteria:
     - `make test` executes both JS and Python test commands with a deterministic runner selection.
     - Required taxonomy targets exist.
     - `quality.json`, `inventory.json`, logs, and `MANIFEST.json` produced.
   - Evidence commands:
     - `python --version`
     - `python -m pip --version`
     - `pytest --version`
     - `node --version`
     - `npm --version`
     - `make setup`
     - `make test`
     - `python scripts/generate_manifest.py`
