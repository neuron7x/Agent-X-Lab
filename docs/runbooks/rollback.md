# Release Rollback Runbook

## Purpose

Use this runbook to roll back a bad release or unstable change set while preserving deterministic evidence.

## Preconditions

- You have the target rollback commit/tag SHA.
- Incident severity and rollback decision are logged.
- Working tree is clean before rollback operations.

## Rollback procedure

1. **Freeze and identify target**
   - Record current SHA and rollback target SHA in incident notes.
   - Confirm target corresponds to last known good build.
2. **Create rollback branch**
   ```bash
   git checkout -b rollback/<YYYYMMDD>-<incident-id>
   ```
3. **Apply rollback**
   - Preferred: revert specific bad commits (preserves history).
     ```bash
     git revert <bad_sha_1> <bad_sha_2>
     ```
   - Emergency: restore known-good state from target SHA.
     ```bash
     git reset --hard <known_good_sha>
     ```
4. **Rebuild proof artifacts**
   ```bash
   python tools/generate_titan9_proof.py --repo-root . --cycles 3
   ```
5. **Run deterministic gates**
   ```bash
   make check
   make proof
   ```
6. **Publish rollback evidence**
   - Commit rollback changes and regenerated artifacts.
   - Link all evidence paths in PR/incident timeline.

## Post-rollback verification

Run and archive results for:

1. `artifacts/titan9/proof.log` contains no failed command sequence.
2. `artifacts/titan9/hashes.json` matches rollback commit expectations.
3. `artifacts/titan9/inventory.json` and `artifacts/titan9/readme_commands.json` are present and updated.
4. Required gates pass (`make check`, `make proof`).
5. No unexpected tracked-file drift (`git status --short` clean after commit).

## Fast evidence map

- Gate/proof execution timeline: `artifacts/titan9/proof.log`
- Current deterministic file hashes: `artifacts/titan9/hashes.json`
- Inventory of tracked outputs: `artifacts/titan9/inventory.json`
- README command contract snapshot: `artifacts/titan9/readme_commands.json`
- Proof generator entrypoint: `tools/generate_titan9_proof.py`
