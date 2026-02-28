# PROD_SPEC_V2.1 CI Gate Fix Addendum

## WHAT
- Reworked the `Evaluate RRD status` workflow step to use an inline `python3 -c` command, removing the fragile heredoc block and eliminating heredoc-closure parser risks.
- Added deterministic `rebuild.log` generation in CI at both evidence locations:
  - `artifacts/rebuild.log`
  - `build_proof/prod_spec/rebuild.log`
- Added explicit assertions that both rebuild logs exist and are non-empty before gate evaluation.
- Collected an auditable proof bundle under `build_proof/prod_spec_fix_pr/outputs/*`.

## WHY
- Unblock CI failures caused by workflow shell parsing instability and missing `rebuild.log` evidence.
- Ensure G1 is deterministically satisfied with concrete evidence artifacts, while preserving fail-closed behavior for hard blockers.
- Preserve deterministic, machine-auditable evidence for G5 ARB approval state verification.

## EVIDENCE
- Baseline and allowlist isolation: `build_proof/prod_spec_fix_pr/outputs/00_git_baseline.txt`
- Gate run output + exit code: `build_proof/prod_spec_fix_pr/outputs/01_prod_spec_gate_run.txt`
- Artifact listing: `build_proof/prod_spec_fix_pr/outputs/02_artifacts_ls.txt`
- Rebuild log generation proof: `build_proof/prod_spec_fix_pr/outputs/03_rebuild_log_generation.txt`
- ARB memo approved-state extraction: `build_proof/prod_spec_fix_pr/outputs/04_arb_memo_update.txt`
- Workflow YAML syntax parse check: `build_proof/prod_spec_fix_pr/outputs/05_workflow_syntax_check.txt`
- Gate report path: `build_proof/prod_spec/gate_check.report.json`

## COMPAT
- No runtime product behavior changes (UI/Worker/Engine execution semantics unchanged).
- Changes are CI/workflow + evidence only; gate checker semantics were not broadened to claim PASS without evidence.
