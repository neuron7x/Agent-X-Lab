# Contributing to AgentX Lab

This repository operates on PR-driven development with deterministic quality gates.
All changes go through the canonical gate sequence before merge.

## Local workflow

```bash
python -m venv .venv
. .venv/bin/activate
make bootstrap
make ci
```

## Before opening a PR

Run the full gate sequence locally:

```bash
make check
make proof
make proof-verify
```

All gates must pass. Zero failures. Zero warnings treated as errors.

## Invariants

- **Fail-closed** — validations must fail on ambiguity; no silent degradation
- **Determinism** — validators and eval harnesses must produce identical outputs on repeat runs
- **Evidence discipline** — keep only reference evidence in git; runtime artifacts are gitignored
- **Atomic PRs** — one concern per PR; do not mix features, fixes, and refactors

## Updating manifests

After changing tracked files, run:

```bash
python scripts/rebuild_checksums.py --repo-root .
```

## Adding a new agent to the catalog

1. Place the agent file in `catalog/agents/`
2. Run `python scripts/rebuild_catalog_index.py --repo-root .` to update `catalog/index.json`
3. Verify with `make validate`

## Gate failures

If a gate fails, fix the root cause. Do not:
- Add `# noqa` or `# type: ignore` without documented justification
- Skip tests or mark them as xfail without a linked issue
- Relax type annotations to avoid mypy errors

## Code style

Enforced by `ruff`. Run `make fmt` to auto-format before committing.
