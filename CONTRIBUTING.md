# Contributing

This repository is optimized for PR-driven development with deterministic quality gates.

## Local workflow

```bash
python -m venv .venv
. .venv/bin/activate
make bootstrap
pre-commit install
make ci
```

## Invariants

- **Fail-closed:** validations must fail on ambiguity.
- **Determinism:** validators and eval harnesses must be reproducible.
- **Evidence discipline:** keep only reference evidence in git; runtime evidence is ignored.

## Updating manifests

After changing tracked files, run:

```bash
python scripts/rebuild_checksums.py --repo-root .
```
