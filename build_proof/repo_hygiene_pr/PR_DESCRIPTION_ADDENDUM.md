## WHAT
- Removed nonessential payload targets: `archive/`, `artifacts/proof_bundle/`, `control-plane/`, `engine/.github/workflows/`.
- Added cryptographic removal manifest and deterministic export runbook under `evidence/removed_payload/`.
- Added gate evidence under `build_proof/repo_hygiene_pr/outputs/` and updated repository hygiene doc.

## WHY
- Reduce repository noise and stale authority surfaces.
- Preserve provenance for removed artifacts while keeping active dependency paths fail-closed.

## EVIDENCE
- `build_proof/repo_hygiene_pr/commands.txt`
- `build_proof/repo_hygiene_pr/outputs/*`
- `evidence/removed_payload/REMOVAL_MANIFEST.json`
- `evidence/removed_payload/EXPORT_RUNBOOK.md`

## COMPAT
- No runtime behavior change under product runtime directories.
- Verification status: local offline-safe checks captured; CI execution explicitly offloaded per policy.
