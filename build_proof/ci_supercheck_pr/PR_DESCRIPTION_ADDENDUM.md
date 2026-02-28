## WHAT
This PR hardens PR safety with three targeted CI changes: (1) eliminates prod-spec fallback report scripting fragility, (2) adds `CI Supercheck` as a deterministic fail-closed aggregator for commit check-runs, and (3) adds workflow-hygiene API pin verification so pinned action SHAs must resolve to real GitHub commits/tarballs.

## WHY
Previous safety gaps allowed non-deterministic CI evidence, check drift, and weak supply-chain pin assurance. The new aggregator enforces context-aware required checks while avoiding docs-only noise and self-deadlock.

## EVIDENCE
- Baseline and repo inventory: `build_proof/ci_supercheck_pr/outputs/00..02`
- Local UI loop: `build_proof/ci_supercheck_pr/outputs/03..07`
- Prod-spec smoke check: `build_proof/ci_supercheck_pr/outputs/08`
- Static pin audit: `build_proof/ci_supercheck_pr/outputs/09`

## COMPAT
No runtime changes to UI/Worker/Engine. This is CI/workflow/docs-only and scoped to allowlisted files.
