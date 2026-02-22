# Incident Response Runbook

## Purpose

This runbook defines how to classify, triage, escalate, and evidence operational incidents in AgentX Lab.

## Severity model

| Severity | Definition | Example trigger | Initial response target |
| --- | --- | --- | --- |
| `SEV-1` | Production or CI safety-critical outage with no safe workaround. | Release/proof pipeline blocked with deterministic gate failures across branches. | Acknowledge in 5 minutes; mitigation in 30 minutes. |
| `SEV-2` | Major degradation with partial workaround. | `make check_r8` fails for required policy checks but repo can still be inspected. | Acknowledge in 15 minutes; mitigation in 2 hours. |
| `SEV-3` | Limited impact or non-critical automation failure. | Single non-release script failure with fallback command available. | Acknowledge in 4 hours; mitigation in 1 business day. |
| `SEV-4` | Cosmetic/documentation issue with no service impact. | Runbook typo, missing docs anchor, stale non-blocking artifact note. | Next planned maintenance window. |

When severity is unclear, fail closed and treat as `SEV-2` until downgraded with evidence.

## Triage algorithm

1. **Detect and freeze context**
   - Capture failing command and exit code.
   - Capture UTC timestamp, branch, and commit SHA.
2. **Classify impact**
   - Determine if deterministic gates (`make check`, `make proof`, `make check_r8`) are blocked.
   - Map impact to severity table above.
3. **Collect primary evidence**
   - Inspect Titan9 proof artifacts:
     - `artifacts/titan9/proof.log`
     - `artifacts/titan9/inventory.json`
     - `artifacts/titan9/hashes.json`
     - `artifacts/titan9/readme_commands.json`
   - Regenerate if needed:
     ```bash
     python tools/generate_titan9_proof.py --repo-root . --cycles 3
     ```
4. **Localize failure domain**
   - If `proof.log` shows command-level failure, route to the failing tool owner.
   - If hashes drift unexpectedly, compare generated and committed files to identify nondeterminism.
   - If inventory mismatch appears, verify tracked outputs in `artifacts/` first.
5. **Mitigate and validate**
   - Apply smallest safe fix or execute rollback runbook when release integrity is at risk.
   - Re-run affected gate(s) and attach outputs.
6. **Close and document**
   - Record root cause, resolution SHA, and evidence file paths in incident notes.

## Escalation path

1. **On-call operator** (owns first triage and severity assignment).
2. **Repository maintainer** (owns fix/rollback decision for `SEV-1` and `SEV-2`).
3. **Security/reliability owner** (required for policy bypass, allowlist changes, or repeated deterministic proof drift).
4. **Release approver** (final sign-off to resume release flow after `SEV-1`).

Escalate immediately (skip waiting targets) when either condition is true:
- deterministic proof generation cannot complete after one mitigation attempt;
- artifact integrity (`artifacts/titan9/hashes.json`) indicates unexplained drift.

## Evidence checklist

- Incident timeline in UTC.
- Failing command + exit code.
- Relevant `artifacts/` files attached or linked.
- Regeneration command and output for `tools/generate_titan9_proof.py`.
- Resolution commit SHA and post-fix gate output.
