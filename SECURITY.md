# Security Policy

## Reporting

If you discover a vulnerability, please open a private security advisory in GitHub or contact the maintainers.

## Supply-chain and release integrity policy

Release artifacts must be reproducible, signed, and verifiable.

- SBOM generation (CycloneDX + SPDX) is required for release bundles.
- SLSA-compatible provenance attestations are required for build outputs.
- Artifact signatures are required and generated with `cosign`.
- Verification is fail-closed via `tools/verify_release_integrity.py`.

See [`docs/supply-chain.md`](docs/supply-chain.md) for operational details and artifact layout.

## Automated checks

- CI quality and repository checks (`.github/workflows/ci.yml`)
- Security policy checks (`.github/workflows/security.yml`)
- Scorecard checks (`.github/workflows/scorecard.yml`)
- Release integrity controls (`.github/workflows/release.yml`)
