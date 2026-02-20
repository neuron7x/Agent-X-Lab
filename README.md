# AgentX Lab

A deterministic cognitive-agent architecture with mechanized validation for shipping prompt catalogs and proof bundles as a GitHub-ready project.

This repository contains:
- a curated **catalog** of top-tier system prompts / protocols (yours + curated packs)
- a minimal **governor CLI** (`sg`) to validate the catalog, run VR calibration, and build a release zip
- a vendored **SCPE CIMQA v2026.3.0** SSOT stack (for interpreted/mechanized quality + evidence discipline)

## Quickstart (local)

```bash
python -m venv .venv
. .venv/bin/activate
make bootstrap
make ci

# fail-closed integrity check
sg --config configs/sg.config.json validate-catalog

# calibration run + evidence bundle + VR.json
sg --config configs/sg.config.json vr

# build release zip (includes latest VR evidence folder when available)
sg --config configs/sg.config.json release
```

Outputs:
- `VR.json`
- `artifacts/evidence/<YYYYMMDD>/<work-id>/...`
- `artifacts/release/*.zip`

## GitHub

Push to GitHub and enable Actions. CI runs:
- catalog integrity (sha256 + indexing)
- pytest-based selftests

## Core “Supreme Command” objects (recommended default stack)
- **DSE Codebase Fixer & Optimizer (99-grade)**: `catalog/agents/06_DSE_Codebase-Fixer-Optimizer_99.txt`
- **Codex PFRI v2026.5.0**: `catalog/agents/CODEX_PFRI_v2026.5.0.md`
- **GHTPO-2026.02**: `catalog/protocols/GHTPO-2026.02.md`

## License
MIT (see LICENSE).


## Evidence tracking policy

- Track only **reference evidence** required for deterministic verification (`objects/*/artifacts/evidence/reference/**`).
- Ignore runtime evidence emitted during local/CI runs (`artifacts/evidence/**`, non-reference object evidence).
