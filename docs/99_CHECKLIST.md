# 99 Checklist {#checklist}

| ItemID | Requirement | Doc section anchor | Evidence anchors | Status |
|---|---|---|---|---|
| CHK-A1 | Critical architecture claims have line-accurate evidence anchors. | docs/01_ARCHITECTURE.md#module-topology | src/App.tsx:L10-L21; src/state/AppStateProvider.tsx:L3-L6 | PASS |
| CHK-A2 | Runtime sequence claims have evidence anchors. | docs/00_SYSTEM_OVERVIEW.md#startup-narrative | src/main.tsx:L4-L9; src/App.tsx:L40-L58 | PASS |
| CHK-A3 | Demo mode behavior is evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#demo-mode | src/state/AppStateProvider.tsx:L33-L36; src/hooks/useGitHubAPI.ts:L225-L227 | PASS |
| CHK-A4 | A11y landmark + command palette contracts are evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#command-palette | src/components/shell/AppShell.tsx:L73-L77; src/components/shell/CommandPalette.tsx:L72-L77; e2e/smoke.spec.ts:L54-L67 | PASS |
| CHK-A5 | Forge behavior claims are evidence-bound. | docs/02_RUNTIME_BEHAVIOR.md#forge-behavior | src/components/axl/ForgeScreen.tsx:L20-L48; src/lib/api.ts:L655-L662 | PASS |
| CHK-B1 | Objective checklist exists and maps requirements to doc/evidence. | docs/99_CHECKLIST.md#checklist | docs/99_CHECKLIST.md:L1-L15 | PASS |
| CHK-C1 | Audit bundle includes gate command transcript file. | docs/06_CI_AND_RELEASE.md#local-gates | build_proof/docs_audit/commands.txt:L1-L16 | PASS |
| CHK-C2 | Audit bundle includes per-gate outputs and CI link file. | docs/06_CI_AND_RELEASE.md#artifact-locations | build_proof/docs_audit/outputs/01_node_version.txt:L1-L2; build_proof/docs_audit/ci_links.txt:L1-L1 | PASS |
| CHK-D1 | No behavior-changing source edits under src/e2e. | docs/07_TROUBLESHOOTING.md#lint-typecheck-fail | build_proof/docs_audit/outputs/04_lint.txt:L1-L7; build_proof/docs_audit/outputs/05_typecheck.txt:L1-L7 | PASS |
| CHK-DRIFT1 | Every listed contract has Implemented-at and Tested-by anchors. | docs/98_CONTRACT_INDEX.md#contract-index | docs/98_CONTRACT_INDEX.md:L3-L79 | PASS |
| CHK-G1 | Baseline gates rerun after doc work with unchanged outcomes. | docs/06_CI_AND_RELEASE.md#local-gates | build_proof/docs_audit/outputs/11_npm_ci_post.txt:L1-L8; build_proof/docs_audit/outputs/16_test_e2e_post.txt:L1-L8 | PASS |
| CHK-LINK1 | Relative links in docs/top-level doc files resolve. | docs/06_CI_AND_RELEASE.md#artifact-locations | build_proof/docs_audit/outputs/17_link_check.txt:L1-L2 | PASS |
