# Disaster Recovery Runbook

## Purpose

Restore repository operations after destructive events (data loss, corrupted artifacts, or prolonged inability to run required gates).

## Recovery objectives

- **RTO (Recovery Time Objective):** 4 hours to restore ability to run `make check` and `make proof` on the default branch.
- **RPO (Recovery Point Objective):** 24 hours maximum proof/artifact data loss.

If either objective is projected to be missed, escalate as `SEV-1`.

## Recovery procedure

1. **Declare disaster and preserve evidence**
   - Capture incident start time, scope, and impacted systems.
   - Snapshot available `artifacts/` and `.git` state.
2. **Restore repository baseline**
   - Recover from trusted remote/default branch mirror.
   - Validate commit integrity of expected recovery point.
3. **Rehydrate critical artifacts**
   - Regenerate Titan9 proof artifacts:
     ```bash
     python tools/generate_titan9_proof.py --repo-root . --cycles 3
     ```
   - Recreate any additional required outputs under `artifacts/` used by release checks.
4. **Run validation gates**
   ```bash
   make check
   make proof
   ```
5. **Compare against recovery objectives**
   - Compute elapsed recovery time versus RTO.
   - Compare recovered commit timestamp versus latest known good point for RPO.
6. **Return to service**
   - Open recovery PR with incident summary and regenerated evidence.
   - Handoff to incident-response process for postmortem.

## Evidence localization guide

When under time pressure, use this order:

1. `artifacts/titan9/proof.log` to locate exact command failures.
2. `artifacts/titan9/hashes.json` to detect integrity drift.
3. `artifacts/titan9/inventory.json` to confirm output completeness.
4. `artifacts/titan9/readme_commands.json` to verify command-contract coverage.
5. `tools/generate_titan9_proof.py` when regeneration is required.

## Exit criteria

Disaster recovery is complete only when all conditions are true:

- required gates pass on recovered branch;
- Titan9 artifacts are regenerated and committed;
- RTO/RPO status is documented;
- incident owner signs off handback to normal operations.
