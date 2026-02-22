# Supply-chain security policy

## Overview

The repository enforces deterministic release-integrity controls around SBOM generation,
provenance attestations, and artifact signing.

## Release controls

- `release.yml` builds release bundles under `artifacts/release/`.
- SBOM files are generated in both formats:
  - CycloneDX: `artifacts/release/sbom.cyclonedx.json`
  - SPDX: `artifacts/release/sbom.spdx.json`
- SLSA-compatible provenance is emitted as:
  - Predicate: `artifacts/release/provenance-predicate.json`
  - in-toto statement bundle: `artifacts/release/provenance.intoto.jsonl`
- The release bundle (`*.tar.gz`) is signed using `cosign`, producing `*.tar.gz.sig`.

## Verification gate

`tools/verify_release_integrity.py` is the mandatory fail-closed gate for release outputs.
The gate validates:

- required files exist in `artifacts/release/`
- exactly one release bundle and signature are present
- checksums in `checksums.txt` match the bundle digest
- SBOM formats are structurally valid (`bomFormat`/`spdxVersion`)
- provenance files contain expected SLSA/in-toto fields

Run locally:

```bash
make release-artifacts
make verify-release-integrity
```

CI enforces this gate in:

- `CI` workflow (`release-integrity` job, fixture validation)
- `Release Integrity` workflow (real release artifacts)
