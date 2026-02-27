# PR Description

## WHAT changed
- Reworked docs/00..07 to be evidence-anchored with explicit `EVIDENCE: path:Lx-Ly` lines for critical claims.
- Added `docs/98_CONTRACT_INDEX.md` with explicit MUST statements and implemented/tested anchors.
- Added `docs/99_CHECKLIST.md` machine-auditable requirement table with PASS/FAIL status.
- Added audit bundle files under `build_proof/docs_audit/` (commands transcript, per-gate outputs, CI link marker).

## WHY
- Eliminate deficits: missing evidence anchors, unverifiable completeness, missing audit bundle, and scope ambiguity.

## EVIDENCE
- Gate transcript: `build_proof/docs_audit/commands.txt`
- Gate outputs: `build_proof/docs_audit/outputs/*.txt`
- CI links marker: `build_proof/docs_audit/ci_links.txt` (LOCAL_ONLY)

## SCOPE constraints confirmation
- No behavior-changing edits in `src/**` or `e2e/**`.
- No dependency or lockfile changes.
- Documentation and audit-bundle files only.
