# Merge Gates

This repository is fail-closed: a merge is allowed only when all deterministic gates pass
through the canonical Makefile path. No exceptions. No bypasses.

## Canonical merge sequence

```bash
make setup
make check
make proof
```

## Gate breakdown (`make check`)

| Gate | Command | Pass condition |
|------|---------|----------------|
| `doctor` | `python tools/doctor.py` | Environment pre-flight clean |
| `format_check` | `ruff format --check .` | Zero formatting drift |
| `lint` | `ruff check .` | Zero lint violations |
| `typecheck` | `mypy .` | `Success: no issues found` |
| `test` | `python -m pytest -q -W error` | Zero failures, zero unhandled warnings |
| `validate` | `python scripts/validate_arsenal.py --repo-root . --strict` | `passed: true` |
| `evals` | `python scripts/run_object_evals.py --repo-root . --write-evidence` | All eval harnesses exit 0 |
| `protocol` | `python tools/verify_protocol_consistency.py --protocol protocol.yaml` | `pass: true` |
| `inventory` | `python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json` | File written |
| `readme_contract` | `python tools/verify_readme_contract.py ...` | Contract satisfied |
| `workflow-hygiene` | `python tools/verify_workflow_hygiene.py` | No hygiene violations |
| `action-pinning` | `python tools/verify_action_pinning.py` | All actions SHA-pinned |
| `secret-scan` | `python tools/secret_scan_gate.py` | Zero secrets detected |

## Proof gate (`make proof`)

```bash
python tools/generate_titan9_proof.py --repo-root .
python tools/derive_proof.py --evidence artifacts/agent/evidence.jsonl --out artifacts/agent/proof.json
```

Proof verification (`make proof-verify`) confirms the derived proof matches the committed proof.

## Contract invariants

- README has exactly one `## Quickstart` section
- Quickstart is Makefile-only and must include `make setup`, `make check`, `make proof`
- CI sets `PYTHONHASHSEED=0` for all tooling steps
- All GitHub Actions must be pinned to a full commit SHA
- No secrets or credentials in any tracked file
- `protocol.yaml` deficit list must exactly match `docs/SPEC.md` deficit list

## Operational policy

- Do not bypass gates locally with skip flags or weakened checks
- If a contract changes, update `tests/` and `docs/` in the same PR
- Keep the command surface deterministic and aligned across Makefile, README, and CI
- If any gate result is UNKNOWN → treat as FAIL
