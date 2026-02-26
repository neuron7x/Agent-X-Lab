# AgentX Lab Naming Conventions (v1.0)

This repository separates **human-readable labels** from **stable machine identifiers**.

## Repo / product

- **Repo name (slug):** `agentx-lab`
- **Product name:** *AgentX Lab*
- **Artifact family:** *AgentX Lab Arsenal* (protocols + objects + validators)

## Agent roles (orchestration)

Formal role IDs (stable):
- **AXL-CREATOR** — generative synthesis (higher temperature)
- **AXL-CRITIC** — adversarial review and gap surfacing (lower temperature)
- **AXL-AUDITOR** — compliance / invariants / evidence (temperature 0)
- **AXL-VERIFIER** — deterministic execution and proof (temperature 0)

Human labels remain: *Creator / Critic / Auditor / Verifier* (for readability).

## Object naming

- Directory: `objects/<object-slug>/`
- Primary spec: `*_IO-BUNDLE_*.md`
- Each object must have:
  - `MANIFEST.json`
  - `eval/` harness + cases + graders
  - `examples/` (happy + adversarial)
  - `evidence/` (optional; generated deterministically)

## Filesystem invariants

- Deterministic checksums are tracked in root `MANIFEST.json` under `checksums`.
- Do not commit volatile caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.venv`).

## Catalog agent filename convention

- Canonical filenames under `catalog/agents/` use **underscored tokens** (for example: `01_PR_Orchestrator_Repo_Readiness_Governor.txt`).
- Hyphenated aliases are not stored as duplicate files. When backwards compatibility is needed, use `catalog/agents/compatibility-aliases.json` to map historical alias filenames to canonical filenames.
- CI guard: `scripts/check_agent_duplicate_content.py` must pass; it fails if two files in `catalog/agents/` are byte-identical.
