## Summary

<!-- One sentence: what does this PR do? -->

## Why

<!-- What problem does this solve or what value does it add? -->

## Changes

<!-- List the files changed and why -->

## Evidence

- [ ] `make check` passes — zero failures
- [ ] `make proof` passes — artifacts generated
- [ ] `make proof-verify` passes — proof matches
- [ ] `python scripts/validate_arsenal.py --repo-root . --strict` — `passed: true`
- [ ] `python -m pytest -q` — 0 failed

## Compatibility

- Python 3.13+
- No new dependencies without updating `requirements.lock`
- No secrets or credentials introduced

## Checklist

- [ ] Docs updated if behavior changed
- [ ] `catalog/index.json` updated if catalog changed (`python scripts/rebuild_catalog_index.py`)
- [ ] `MANIFEST.json` updated if tracked files changed (`python scripts/rebuild_checksums.py`)
