# Contributing

This repository is optimized for PR-driven development with automated gates.

## Local workflow

```bash
make setup
make ci
```

## Invariants

- **Fail-closed:** validations must fail on ambiguity.
- **Determinism:** validators and eval harnesses must be reproducible.
- **Evidence:** PRs must include proof (logs + outputs), not claims.

## Updating manifests

After changing any files, run:

```bash
python scripts/rebuild_checksums.py --repo-root .
```
