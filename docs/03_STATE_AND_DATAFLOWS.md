# 03 State and Data Flows {#state-dataflows}

## 3.1 State-flow diagram {#state-flow}
```text
sessionStorage(axl_demo_mode) -> AppStateProvider -> useGitHubAPI/useArsenal -> screens
localStorage(axl-bff-settings) -> useGitHubSettings -> isConfigured -----------^
```
EVIDENCE: src/state/AppStateProvider.tsx:L15-L37
EVIDENCE: src/hooks/useGitHubSettings.ts:L13-L40

## 3.2 Polling and connection state {#polling-connection-state}
- Query polling is enabled only when configured, non-demo, non-rate-limited.
EVIDENCE: src/hooks/useGitHubAPI.ts:L48-L57
- Connection status derives from fetch/error/rate-limit state machine.
EVIDENCE: src/hooks/useGitHubAPI.ts:L183-L213

## 3.3 Rate-limit and contract failure handling {#rate-limit-failures}
- Rate-limit reset is parsed and polling suspended until reset timestamp.
EVIDENCE: src/hooks/useGitHubAPI.ts:L18-L24
EVIDENCE: src/hooks/useGitHubAPI.ts:L148-L162
- Missing contract file maps to explicit `MISSING_CONTRACT_SSOT` signal.
EVIDENCE: src/hooks/useGitHubAPI.ts:L26-L30
EVIDENCE: src/hooks/useGitHubAPI.ts:L215-L217

## 3.4 Deterministic parsing rules {#deterministic-parsing}
- Evidence lines parser behavior is test-locked (cap=30, malformed counted, status mapping).
EVIDENCE: src/test/example.test.ts:L98-L123
