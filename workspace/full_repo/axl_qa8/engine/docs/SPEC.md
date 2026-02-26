# TITAN-9 R6 Protocol Spec

This repository encodes TITAN-9 remediation mapping as a bijection between deficits and patch steps.
Every deficit maps to exactly one or more protocol steps. Every step maps to exactly one or more
implementation paths. The mapping is machine-validated at every `make check` run.

## Deficits

| ID | Description |
|----|-------------|
| D7_RACE_CONDITION_ID | Non-deterministic identifier generation |
| D8_FRAGILE_DYNAMIC_IMPORT | Unsafe lazy import patterns |
| D9_HIDDEN_STATE_LEAK | Environment or module state leaking between runs |
| D10_SPEC_DRIFT_UNVERIFIED | Spec and implementation diverging without detection |
| D11_DOC_SYNC_GAP | Documentation lagging behind implementation |
| D12_README_DRIFT | README commands diverging from Makefile and CI |
| D13_FORMAT_GATE_FAIL | Formatting not enforced in CI |

## Canonical mapping source

`protocol.yaml` is the machine-readable source validated by `tools/verify_protocol_consistency.py`.
The validator checks:
- No duplicate deficit IDs
- No missing deficits referenced by steps
- No orphan steps referencing nonexistent deficits
- All `impl_paths` exist in the repository

## README SSOT contract

README must contain exactly one `## Quickstart` section with executable commands.
Quickstart is Makefile-only and must include `make setup`, `make check`, and `make proof`.
Contract is enforced by `tools/verify_readme_contract.py` against CI workflows and generated inventory.

## Proof bundle artifacts

`tools/generate_titan9_proof.py` generates deterministic outputs in `artifacts/titan9/`:

- `inventory.json` — full file registry with hashes
- `readme_commands.json` — extracted and validated Quickstart commands
- `proof.log` — execution log with timestamps and exit codes
- `hashes.json` — SHA-256 registry for all tracked files

All four files must be present and non-empty for proof to be valid.

## Verification record (VR) schema

`VR.json` is written by `sg vr` and contains:

- `schema` — version identifier (`VR-2026.1`)
- `utc` — ISO-8601 timestamp of the run
- `status` — `RUN` (all gates pass) or `CALIBRATION_REQUIRED` (blockers present)
- `work_id` — git commit SHA or `release-<version>+nogit.<digest>`
- `metrics` — catalog validity, baseline pass rate, evidence count
- `blockers` — list of blocking conditions if status is not `RUN`
