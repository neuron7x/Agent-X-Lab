# Repository Hygiene

## Scope directories
- `archive/`: historical payloads; not part of lint/test runtime checks.
- `artifacts/`: generated build/test outputs.
- `evidence/`: immutable verification outputs per PR.

## Rules
1. No zip in git for new changes (`*.zip` prohibited for new additions).
2. Checksums only for transferred binaries where required.
3. Size limit: tracked file threshold is 5 MB for baseline detection.
4. Rotation: generated evidence/artifacts must be rotated by PR lifecycle and not overwritten silently.

## Guardrails
- Run large-file scanner against tracked files.
- Run secret scanner against tracked files.
- Keep scan output serialized in `evidence/TD0_BASELINE.json`.
