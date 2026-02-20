# AgentX Lab (v1.1.0)

**AgentX Lab** is an **audit-grade, fail-closed arsenal** for shipping *agent systems as engineering artifacts*:
- deterministic protocols (`protocols/`)
- multi-agent orchestration specs (`architecture/`)
- deployable objects with eval harnesses, cases, graders, and evidence (`objects/*/`)
- mechanized validators and CI gates (scripts + GitHub Actions)

This repo is designed for **high-stakes agent work** where *interpretability, reproducibility, and merge-time safety* matter.
It can be used as a foundation for applied domains (e.g., marketing/perception research workflows), without claiming
any scientific validity beyond what is explicitly evaluated in `objects/*/eval/`.

## Quickstart

```bash
make setup
make ci
```

Minimal (no venv):

```bash
python -m pip install -r requirements-dev.txt
make validate
make eval
```

## CI / PR Quality Gates

- **lint**: `ruff` + `actionlint` + JSON schema validation
- **typecheck**: `mypy`
- **tests**: `pytest`
- **arsenal validation**: `scripts/validate_arsenal.py --strict`
- **object evals**: `scripts/run_object_evals.py`

GitHub Actions:
- `.github/workflows/ci.yml` (main gates)
- `.github/workflows/dependency-review.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/gitleaks.yml`

## Repository layout

- `protocols/` — canonical protocols (IOPS-2026, ENC-CORE)
- `architecture/` — orchestration + system contracts
- `objects/*/` — deployable objects (IO-BUNDLE + eval + cases + graders + evidence)
- `schemas/` — JSON Schemas for manifests and eval evidence
- `scripts/` — validators, harness runners, packager CLI
- `catalog/` — curated inventories (agents/protocols/stacks)
- `tools/` — auxiliary stacks and legacy catalog mirrors

## Creating a new object

1. Copy an existing object directory as a template.
2. Update `objects/<name>/MANIFEST.json`.
3. Add:
   - `eval/run_harness.py`
   - `eval/cases/*.json`
   - `eval/graders.py`
   - `examples/` (happy + adversarial)
4. Run:
   ```bash
   make ci
   python scripts/rebuild_checksums.py --repo-root .
   ```

## License

MIT. See `LICENSE`.
