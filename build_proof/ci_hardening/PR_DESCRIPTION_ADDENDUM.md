## CI Security + Workflow Quality Gate Hardening Addendum

### WHAT changed
- Added four hardened workflows: `CodeQL Analysis`, `Dependency Review`, `Secret Scan (Gitleaks)`, and `Workflow Hygiene` with explicit permissions, concurrency cancellation, workflow_dispatch, and job timeouts.
- Corrected Workflow Hygiene action source to `reviewdog/action-actionlint`.
- Aligned dependency and secret scanning to low-noise mode (no PR comments; output/artifact/SARIF-driven).
- Added docs and evidence bundle under `docs/08_SECURITY_GATES.md` and `build_proof/ci_hardening/**`.

### WHY
- Enforce deterministic, least-privilege, reproducible security gates.
- Reduce CI noise while preserving fail-closed signals and auditable outputs.
- Provide machine-checkable evidence mapping for reviewer verification.

### EVIDENCE
- Workflow definitions: `.github/workflows/{codeql-analysis.yml,dependency-review.yml,secret-scan.yml,workflow-hygiene.yml}`
- Audit outputs: `build_proof/ci_hardening/outputs/`
- CI links:
  - https://github.com/neuron7x/Agent-X-Lab/actions/runs/22500920063/job/65187507908?pr=97
  - https://github.com/neuron7x/Agent-X-Lab/actions/runs/22500920069/job/65187507974?pr=97

### SCOPE confirmation
- Changed only workflow, documentation, and evidence files.
- No edits under forbidden runtime/source paths.
