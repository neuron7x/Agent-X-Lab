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
CodeQL uses valid `github/codeql-action` v4.32.4 commit pins for `init` and `analyze`, with explicit JS+Python setup and `build-mode: none` for deterministic interpreted-language analysis.
EVIDENCE: .github/workflows/codeql-analysis.yml:L37-L65
Secret scan uses the same valid CodeQL action commit for `upload-sarif`, eliminating action resolution failures caused by invalid pins.
EVIDENCE: .github/workflows/secret-scan.yml:L39-L43
Workflow Hygiene grants only the additional `checks: write` scope required for `reviewdog` check-run publication.
EVIDENCE: .github/workflows/workflow-hygiene.yml:L25-L36

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
Current fail-closed state: two unpinned refs remain in `.github/workflows/ui-perf.yml` (`actions/setup-node@v4`), which is outside the current allowed edit scope in this task.
EVIDENCE: build_proof/ci_hardening/outputs/01_action_pin_audit.txt:L28-L31
EVIDENCE: build_proof/ci_hardening/outputs/12_not_pinned_check.txt:L1-L4


## 8.5 Evidence limitations and blockers {#security-evidence-limitations}
This environment still cannot fetch GitHub Actions logs/API (`CONNECT tunnel failed, response 403`) and has no `gh` CLI, so green-status verification for PR jobs remains blocked.
EVIDENCE: build_proof/ci_hardening/outputs/13_ci_log_access_check.txt:L1-L3
EVIDENCE: build_proof/ci_hardening/outputs/09_gh_cli_check.txt:L1-L6
Local `actionlint` binary is not available in this environment, so CHK-CI-G6B remains fail-closed pending CI-log or local-binary proof.
EVIDENCE: build_proof/ci_hardening/outputs/07_actionlint__version.txt:L1-L3
