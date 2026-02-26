# ARCHITECTURE — AgentX Lab

## Purpose

AgentX Lab is a deterministic governance and proof system for cognitive-agent catalogs.
The repository is optimized for **repeatability**, **traceability**, and **mechanized verification**.

**Core design axiom:** outcome over output. Every process emits evidence. Every gate is fail-closed.
Ambiguity is treated as a blocker, not a default.

## Core design principles

- **Determinism first** — `PYTHONHASHSEED=0` is exported in `Makefile` and CI; all outputs are reproducible
- **Single-path onboarding** — one canonical contributor flow: `make setup` → `make check` → `make proof`
- **Evidence-bound outputs** — validation and proof commands emit auditable artifacts under `artifacts/`
- **Protocol consistency** — `protocol.yaml` is machine-validated against documentation and tooling
- **Fail-closed gates** — UNKNOWN or ambiguous input → STOP; no silent degradation
- **Human judgment over automation** — AI tooling handles grunt work; decisions require evidence

## Repository topology

```
exoneural_governor/   — runtime package: CLI, VR, catalog, config, release, redaction
tools/                — deterministic verification: inventory, proof, protocol, gates
scripts/              — evaluation orchestration and validation
docs/                 — SSOT documentation: spec, architecture, gates, errors
tests/                — regression and contract tests
catalog/              — agent prompts, stacks, protocols
architecture/         — adversarial orchestration and cognitive contract specs
.github/workflows/    — CI: setup → check → proof → verify
configs/              — sg.config.json with schema
schemas/              — JSON schemas for manifests and eval reports
policies/             — pip audit allowlist, action pinning policy
vendor/               — pinned external quality tooling (scpe-cimqa-2026.3.0)
```

## Execution graph

```
make setup
  └─ pip install requirements.lock + requirements-dev.txt

make check
  ├─ doctor           → environment pre-flight
  ├─ format_check     → ruff format --check
  ├─ lint             → ruff check
  ├─ typecheck        → mypy
  ├─ test             → pytest -W error
  ├─ validate         → validate_arsenal.py --strict
  ├─ evals            → run_object_evals.py --write-evidence
  ├─ protocol         → verify_protocol_consistency.py
  ├─ inventory        → titan9_inventory.py
  ├─ readme_contract  → verify_readme_contract.py
  ├─ workflow-hygiene → verify_workflow_hygiene.py
  ├─ action-pinning   → verify_action_pinning.py
  └─ secret-scan      → secret_scan_gate.py

make proof
  ├─ generate_titan9_proof.py
  └─ derive_proof.py
```

## Deterministic interfaces

- **Makefile** is the onboarding SSOT — all operations go through Make targets
- **README Quickstart** references Make targets only — no raw commands
- **CI** mirrors Make targets exactly to prevent contract drift
- **Error catalog** in `docs/ERRORS.md` is the SSOT for all user-facing error identifiers
- **`protocol.yaml`** is the machine-readable source for deficit → step mapping

## Adversarial orchestration model

Catalog artifacts are produced and verified through a four-role adversarial pipeline:

| Role | Bias | Function |
|------|------|----------|
| Creator | Completeness | Generates candidate artifact |
| Critic | Adversarial | Finds structural failures |
| Auditor | Policy | Verifies invariants and constraints |
| Verifier | Reproducibility | Confirms outputs are deterministic |

Quality emerges from structured disagreement, not consensus.
See `architecture/ADVERSARIAL-ORCHESTRATION.md` for the full specification.

## Cognitive contracts

Every agent in the catalog adheres to a three-part contract:

- **Input contract** — required fields, scope, forbidden inputs
- **Output contract** — required structure, stable identifiers, determinism requirements
- **Failure contract** — fail-closed: UNKNOWN → STOP with reason and next action

See `architecture/COGNITIVE-CONTRACTS.md` for the full specification.

## Artifacts and provenance

| Artifact | Path | Purpose |
|----------|------|---------|
| Verification record | `VR.json` | Run status, metrics, blockers |
| Inventory | `artifacts/titan9/inventory.json` | Full file registry |
| Proof log | `artifacts/titan9/proof.log` | Command provenance |
| Hash registry | `artifacts/titan9/hashes.json` | Deterministic file hashes |
| Evidence tree | `artifacts/evidence/<tag>/<work-id>/` | Auditable run artifacts |
| Release bundle | `artifacts/release/*.zip` | Shippable output |
