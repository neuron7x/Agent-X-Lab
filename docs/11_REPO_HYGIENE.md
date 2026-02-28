# Repository Hygiene (Payload Removal)

## What was removed
- `archive/`
- `artifacts/proof_bundle/`
- `control-plane/`
- `engine/.github/workflows/`

## Why
These trees were historical or non-authoritative payload that are not consumed by active CI/gate/runtime paths in this repository.

## Provenance retained
- Removal manifest (SHA-256 per file): `evidence/removed_payload/REMOVAL_MANIFEST.json`
- Deterministic recovery runbook: `evidence/removed_payload/EXPORT_RUNBOOK.md`
- Gate evidence and scans: `build_proof/repo_hygiene_pr/outputs/`

## Non-claims
This change does not claim any external archival upload. Recovery is from git history only.
