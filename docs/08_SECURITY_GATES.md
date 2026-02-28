# 08 Security Gates {#security-gates}

## 8.1 Workflow inventory and check names {#security-workflow-inventory}
The security/quality gate workflow names are `CodeQL Analysis`, `Dependency Review`, `Secret Scan (Gitleaks)`, and `Workflow Hygiene`.
EVIDENCE: .github/workflows/codeql-analysis.yml:L1
EVIDENCE: .github/workflows/dependency-review.yml:L1
EVIDENCE: .github/workflows/secret-scan.yml:L1
EVIDENCE: .github/workflows/workflow-hygiene.yml:L1

## 8.2 Correctness hardening decisions {#security-correctness}
Workflow Hygiene uses `reviewdog/action-actionlint` (not `reviewdog/actionlint`) with `github-pr-check` reporter, so no PR comment permission is required.
EVIDENCE: .github/workflows/workflow-hygiene.yml:L28-L33
Dependency Review sets `comment-summary-in-pr: never`, and therefore keeps `pull-requests: read` for low-noise, least-privilege behavior.
EVIDENCE: .github/workflows/dependency-review.yml:L19-L24
Secret scan disables PR comments and uploads SARIF with explicit `security-events: write` permission for deterministic scan output.
EVIDENCE: .github/workflows/secret-scan.yml:L21-L42
CodeQL uses v4 action references with explicit JS+Python setup and `build-mode: none` for deterministic interpreted-language analysis.
EVIDENCE: .github/workflows/codeql-analysis.yml:L37-L63

## 8.3 Determinism and run-noise controls {#security-determinism}
Each gate workflow includes `workflow_dispatch`, `concurrency` cancellation by ref, explicit `permissions`, and `timeout-minutes`.
EVIDENCE: .github/workflows/codeql-analysis.yml:L3-L36
EVIDENCE: .github/workflows/dependency-review.yml:L3-L18
EVIDENCE: .github/workflows/secret-scan.yml:L3-L25
EVIDENCE: .github/workflows/workflow-hygiene.yml:L3-L24
Heavy scanners skip docs-only changes with `paths-ignore` on `docs/**`, `build_proof/**`, and `**/*.md`.
EVIDENCE: .github/workflows/codeql-analysis.yml:L6-L14
EVIDENCE: .github/workflows/dependency-review.yml:L4-L8
EVIDENCE: .github/workflows/secret-scan.yml:L4-L8

## 8.4 Supply-chain pinning evidence {#security-pinning}
Action pin audit output is recorded at `build_proof/ci_hardening/outputs/01_action_pin_audit.txt` and classifies every `uses:` reference as `SHA_PINNED` or `NOT_PINNED`.
EVIDENCE: build_proof/ci_hardening/outputs/01_action_pin_audit.txt:L1-L30


## 8.5 Evidence limitations and blockers {#security-evidence-limitations}
This environment cannot access github.com Actions logs/API (`CONNECT tunnel failed, response 403`), and `gh` CLI is not installed, so decisive root-cause extraction and rerun verification for PR jobs are blocked.
EVIDENCE: build_proof/ci_hardening/outputs/00_ci_failures_root_cause.txt:L1-L24
Attempting deterministic local actionlint install via Go also fails because module fetch is forbidden, so CHK-CI-G6B cannot be promoted to PASS in this environment.
EVIDENCE: build_proof/ci_hardening/outputs/08_blocker_network_and_actionlint_install.txt:L1-L8
