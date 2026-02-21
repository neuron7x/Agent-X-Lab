# ARCHITECTURE — AgentX Lab

## Purpose

AgentX Lab is a deterministic governance and proof system for cognitive-agent catalogs. The repository is optimized for **repeatability**, **traceability**, and **mechanized verification**.

## Core design principles

- **Determinism first**: `PYTHONHASHSEED=0` is exported in `Makefile` and CI, so command outputs are reproducible.
- **Single-path onboarding**: one canonical flow for contributors:
  - `make setup`
  - `make check`
  - `make proof`
- **Evidence-bound outputs**: validation and proof commands emit auditable artifacts under `artifacts/`.
- **Protocol consistency**: `protocol.yaml` is machine-validated against documentation and check scripts.

## Repository topology

- `exoneural_governor/` — runtime and CLI package implementation.
- `tools/` — deterministic verification tooling (inventory, README contract, protocol consistency, proof generation).
- `scripts/` — domain validation and evaluation orchestration.
- `docs/` — SSOT documentation for spec, architecture, merge gates, and deterministic errors.
- `tests/` — regression and contract tests for tooling and governance behavior.
- `.github/workflows/` — CI execution of setup/check/proof.

## Execution graph

1. **Setup** (`make setup`)
   - installs pinned runtime/dev dependencies via `python -m pip`.
2. **Quality gates** (`make check`)
   - formatting, linting, typing, tests, arsenal validation, evals, protocol consistency, inventory generation, README contract checks.
3. **Proof bundle** (`make proof`)
   - emits deterministic Titan9 proof artifacts in `artifacts/titan9/`.

## Deterministic interfaces

- **Makefile** is the onboarding SSOT.
- **README Quickstart** references Make targets only.
- **CI** mirrors Make targets (`make setup`, `make check`, `make proof`) to avoid contract drift.
- **Error catalog** in `docs/ERRORS.md` is the deterministic message SSOT.

## Artifacts and provenance

Key proof outputs include:

- `artifacts/titan9/inventory.json`
- `artifacts/titan9/readme_commands.json`
- `artifacts/titan9/proof.log`
- `artifacts/titan9/hashes.json`

These artifacts provide command provenance, contract evidence, and deterministic file hashes suitable for release and audit workflows.
