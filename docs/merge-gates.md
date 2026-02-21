# Merge Gates

This repository is fail-closed: a merge is allowed only when deterministic gates pass through the canonical Makefile path.

## Canonical merge sequence

```bash
make setup
make check
make proof
```

## Gate breakdown (`make check`)

- `make format_check` → `ruff format --check .`
- `make lint` → `ruff check .`
- `make typecheck` → `mypy .`
- `make test` → `python -m pytest -q -W error`
- `make validate` → `python scripts/validate_arsenal.py --repo-root . --strict`
- `make evals` → `python scripts/run_object_evals.py --repo-root . --write-evidence`
- `make protocol` → `python tools/verify_protocol_consistency.py --protocol protocol.yaml`
- `make inventory` → `python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json`
- `make readme_contract` →
  `python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json`

## Proof gate (`make proof`)

- `python tools/generate_titan9_proof.py --repo-root .`

## Contract invariants

- README has exactly one `## Quickstart` section.
- Quickstart is Makefile-only and must include:
  - `make setup`
  - `make check`
  - `make proof`
- CI sets `PYTHONHASHSEED=0` for tooling steps.
- README-linked local docs/scripts paths must exist.

## Operational policy

- Do not bypass gates locally with skips or weakened checks.
- If contracts change, update tests in `tests/` and documentation in `docs/` in the same PR.
- Keep the command surface deterministic and aligned across Makefile, README, and CI.
