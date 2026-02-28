# 99 Checklist {#checklist}

| ItemID | Requirement | Doc section anchor | Evidence anchors | Status |
|---|---|---|---|---|
| CHK-A1 | Critical architecture claims have line-accurate evidence anchors. | docs/01_ARCHITECTURE.md#module-topology | src/App.tsx:L10-L21; src/state/AppStateProvider.tsx:L3-L6 | PASS |
| CHK-A2 | Runtime sequence claims have evidence anchors. | docs/00_SYSTEM_OVERVIEW.md#startup-narrative | src/main.tsx:L4-L9; src/App.tsx:L40-L58 | PASS |
| CHK-A3 | Demo mode behavior is evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#demo-mode | src/state/AppStateProvider.tsx:L33-L36; src/hooks/useGitHubAPI.ts:L225-L227 | PASS |
| CHK-A4 | A11y landmark + command palette contracts are evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#command-palette | src/components/shell/AppShell.tsx:L73-L77; src/components/shell/CommandPalette.tsx:L72-L77; e2e/smoke.spec.ts:L54-L67 | PASS |
| CHK-A5 | Forge behavior claims are evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#forge-behavior | src/components/axl/ForgeScreen.tsx:L20-L48; src/lib/api.ts:L655-L662 | PASS |
| CHK-B1 | Objective checklist exists and maps requirements to doc/evidence. | docs/99_CHECKLIST.md#checklist | docs/99_CHECKLIST.md:L1-L35 | PASS |
| CHK-C1 | Audit bundle includes gate command transcript file. | docs/06_CI_AND_RELEASE.md#local-gates | build_proof/docs_audit/commands.txt:L1-L16 | PASS |
| CHK-C2 | Audit bundle includes per-gate outputs and CI link file. | docs/06_CI_AND_RELEASE.md#artifact-locations | build_proof/docs_audit/outputs/01_node_version.txt:L1-L2; build_proof/docs_audit/ci_links.txt:L1-L1 | PASS |
| CHK-D1 | No behavior-changing source edits under src/e2e. | docs/07_TROUBLESHOOTING.md#lint-typecheck-fail | build_proof/docs_audit/outputs/04_lint.txt:L1-L7; build_proof/docs_audit/outputs/05_typecheck.txt:L1-L7 | PASS |
| CHK-DRIFT1 | Every listed contract has Implemented-at and Tested-by anchors. | docs/98_CONTRACT_INDEX.md#contract-index | docs/98_CONTRACT_INDEX.md:L3-L79 | PASS |
| CHK-G1 | Baseline gates rerun after doc work with unchanged outcomes. | docs/06_CI_AND_RELEASE.md#local-gates | build_proof/docs_audit/outputs/11_npm_ci_post.txt:L1-L8; build_proof/docs_audit/outputs/16_test_e2e_post.txt:L1-L8 | PASS |
| CHK-LINK1 | Relative links in docs/top-level doc files resolve. | docs/06_CI_AND_RELEASE.md#artifact-locations | build_proof/docs_audit/outputs/17_link_check.txt:L1-L2 | PASS |

## CI hardening checklist (PR #97)

| ItemID | Requirement | Doc section anchor | Evidence anchors | Status |
|---|---|---|---|---|
| CHK-CI-G0 | Inventory JSON exists with workflows/docs/evidence lists. | docs/08_SECURITY_GATES.md#security-workflow-inventory | build_proof/ci_hardening/INVENTORY.json:L1-L34 | PASS |
| CHK-CI-G1A | Workflow Hygiene uses correct action repo (`reviewdog/action-actionlint`). | docs/08_SECURITY_GATES.md#security-correctness | .github/workflows/workflow-hygiene.yml:L32-L35 | PASS |
| CHK-CI-G1B | Dependency Review permission/input alignment is low-noise (`comment-summary-in-pr: never`, PR read-only). | docs/08_SECURITY_GATES.md#security-correctness | .github/workflows/dependency-review.yml:L19-L24 | PASS |
| CHK-CI-G1C | Secret scan output strategy is deterministic, no PR comment noise, SARIF upload permitted. | docs/08_SECURITY_GATES.md#security-correctness | .github/workflows/secret-scan.yml:L21-L42 | PASS |
| CHK-CI-G1D | CodeQL upgraded to v4 references with deterministic language setup and manual trigger. | docs/08_SECURITY_GATES.md#security-correctness | .github/workflows/codeql-analysis.yml:L3-L63 | PASS |
| CHK-CI-G2 | Explicit permissions + timeout + concurrency + workflow_dispatch on each new workflow. | docs/08_SECURITY_GATES.md#security-determinism | .github/workflows/codeql-analysis.yml:L3-L36; .github/workflows/dependency-review.yml:L3-L18; .github/workflows/secret-scan.yml:L3-L25; .github/workflows/workflow-hygiene.yml:L3-L24 | PASS |
| CHK-CI-G3 | All `uses:` entries SHA-pinned. | docs/08_SECURITY_GATES.md#security-pinning | build_proof/ci_hardening/outputs/01_action_pin_audit.txt:L1-L33; build_proof/ci_hardening/outputs/12_not_pinned_check.txt:L1-L4 | FAIL (`.github/workflows/ui-perf.yml` has unpinned `actions/setup-node@v4` on two lines; file is outside current allowed edit scope). |
| CHK-CI-G4 | Path filters reduce docs-only run noise for heavy scanners. | docs/08_SECURITY_GATES.md#security-determinism | .github/workflows/codeql-analysis.yml:L6-L14; .github/workflows/dependency-review.yml:L4-L8; .github/workflows/secret-scan.yml:L4-L8 | PASS |
| CHK-CI-G5 | CI gate docs include evidence anchors for critical claims. | docs/08_SECURITY_GATES.md#security-gates | docs/08_SECURITY_GATES.md:L1-L33 | PASS |
| CHK-CI-G6A | Required command transcript and per-command outputs recorded with exit codes. | docs/06_CI_AND_RELEASE.md#security-gates-hardening | build_proof/ci_hardening/commands.txt:L1-L7; build_proof/ci_hardening/outputs/01_node___version.txt:L1-L3; build_proof/ci_hardening/outputs/06_npm_test.txt:L1-L9 | PASS |
| CHK-CI-G6B | `actionlint` command executed locally. | docs/06_CI_AND_RELEASE.md#security-gates-hardening | build_proof/ci_hardening/outputs/07_actionlint__version.txt:L1-L3 | FAIL (binary unavailable in environment; CI log proof also blocked). |
| CHK-CI-G6C | Required CI run URLs captured in evidence bundle. | docs/06_CI_AND_RELEASE.md#security-gates-hardening | build_proof/ci_hardening/ci_links.txt:L1-L2 | PASS |
| CHK-CI-G7 | README quality-gates names match workflow `name:` values exactly. | docs/08_SECURITY_GATES.md#security-workflow-inventory | README.md:L33-L40; .github/workflows/codeql-analysis.yml:L1; .github/workflows/dependency-review.yml:L1; .github/workflows/secret-scan.yml:L1; .github/workflows/workflow-hygiene.yml:L1 | PASS |
| CHK-CI-G8 | PR addendum present with WHAT/WHY/EVIDENCE/SCOPE. | docs/08_SECURITY_GATES.md#security-gates | build_proof/ci_hardening/PR_DESCRIPTION_ADDENDUM.md:L1-L27 | PASS |


## Blocking constraints (fail-closed)

| ItemID | Requirement | Doc section anchor | Evidence anchors | Status |
|---|---|---|---|---|
| CHK-CI-BLOCK-LOGS | Decisive per-job error excerpts captured from failing GitHub Actions runs. | docs/08_SECURITY_GATES.md#security-evidence-limitations | build_proof/ci_hardening/outputs/00_ci_failures_root_cause.txt:L1-L20; build_proof/ci_hardening/outputs/13_ci_log_access_check.txt:L1-L3 | FAIL (cannot fetch Actions job logs from this environment). |
| CHK-CI-BLOCK-ACTIONLINT-INSTALL | Local actionlint install/execution for CHK-CI-G6B. | docs/08_SECURITY_GATES.md#security-evidence-limitations | build_proof/ci_hardening/outputs/07_actionlint__version.txt:L1-L3 | FAIL (actionlint binary unavailable; install path blocked). |
| CHK-CI-BLOCK-CI-PASS | Proof that all required PR checks are green for PR #100 branch. | docs/08_SECURITY_GATES.md#security-evidence-limitations | build_proof/ci_hardening/ci_links.txt:L1-L2; build_proof/ci_hardening/outputs/09_gh_cli_check.txt:L1-L6; build_proof/ci_hardening/outputs/13_ci_log_access_check.txt:L1-L3 | FAIL (cannot query or observe reruns from this environment). |
