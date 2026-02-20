# TITAN-9 R6 Protocol Spec

This repository encodes TITAN-9 remediation mapping as a bijection between deficits and patch steps.

## Deficits

- D7_RACE_CONDITION_ID
- D8_FRAGILE_DYNAMIC_IMPORT
- D9_HIDDEN_STATE_LEAK
- D10_SPEC_DRIFT_UNVERIFIED
- D11_DOC_SYNC_GAP
- D12_README_DRIFT
- D13_FORMAT_GATE_FAIL

## Canonical mapping source

`protocol.yaml` is the machine-readable source used by `tools/verify_protocol_consistency.py`.

## README SSOT contract

README must contain exactly one `## Quickstart` section with executable commands.
Contract is enforced by `tools/verify_readme_contract.py` against CI workflows and generated inventory.


## Proof bundle artifacts

`tools/generate_titan9_proof.py` must generate deterministic outputs in `artifacts/titan9/`: `inventory.json`, `readme_commands.json`, `proof.log`, and `hashes.json`.
