# Release Policy

## Scope and Source of Truth

- `pyproject.toml` (`[project].version`) is the canonical version for this repository.
- `CHANGELOG.md` must contain the release entry for that exact version before a release job can proceed.
- `docs/release-notes.md` must contain human-readable release notes for that exact version before a release job can proceed.

## Semantic Versioning Rules

This project follows SemVer: `MAJOR.MINOR.PATCH`.

### MAJOR bump (`X.0.0`)

Use when introducing backward-incompatible changes, including:

- Removed or renamed public CLI commands/options.
- Breaking schema changes in documented JSON/YAML interfaces.
- Behavior changes that invalidate existing automation contracts.

### MINOR bump (`0.Y.0`)

Use when adding backward-compatible functionality, including:

- New commands/options that do not change existing defaults.
- New optional fields in stable schemas.
- New additive automation/report outputs.

### PATCH bump (`0.0.Z`)

Use for backward-compatible fixes only:

- Bug fixes without API/contract breakage.
- Security fixes that preserve existing interfaces.
- Documentation-only and maintenance changes.

## Change Types and Changelog Mapping

Each released version in `CHANGELOG.md` must include sections as applicable:

- `Added`
- `Changed`
- `Fixed`
- `Security`

`docs/release-notes.md` should summarize operator-facing impact, risk, and rollout notes.

## Backward Compatibility Expectations

- Public CLI and documented protocol artifacts should remain stable across PATCH and MINOR releases.
- If compatibility cannot be preserved, the change must be explicitly called out as **Breaking** in both changelog and release notes, and the version must be MAJOR.
- Any migration steps must be documented in `docs/release-notes.md`.

## Version Bump Workflow

1. Update `[project].version` in `pyproject.toml`.
2. Move notable entries from `CHANGELOG.md` `Unreleased` into `## [<version>] - <YYYY-MM-DD>`.
3. Add/update matching `## <version>` section in `docs/release-notes.md`.
4. Open PR with these updates.
5. Release automation validates version and documentation alignment before building release artifacts.
