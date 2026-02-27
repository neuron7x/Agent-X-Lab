# 01 Architecture {#architecture}

## 1.1 Module topology {#module-topology}
```text
App
 ├─ AppStateProvider
 │   ├─ useGitHubSettings
 │   ├─ useGitHubAPI
 │   └─ useArsenal
 ├─ AppShell
 │   └─ CommandPalette
 └─ lazy routes (modules/*)
```
EVIDENCE: src/App.tsx:L10-L21
EVIDENCE: src/state/AppStateProvider.tsx:L3-L6
EVIDENCE: src/components/shell/AppShell.tsx:L11-L18
EVIDENCE: src/modules/index.ts:L8-L13

## 1.2 Shell and route contracts {#shell-routes}
- All declared routes are rendered inside `AppShell`.
EVIDENCE: src/App.tsx:L48-L56
- `AppShell` owns `navigation` and `main` landmarks and skip-link target.
EVIDENCE: src/components/shell/AppShell.tsx:L48-L53
EVIDENCE: src/components/shell/AppShell.tsx:L73-L77
EVIDENCE: src/components/shell/AppShell.tsx:L103-L105

## 1.3 State providers and persistence {#state-persistence}
- Demo mode preference key: `axl_demo_mode` in sessionStorage.
EVIDENCE: src/state/AppStateProvider.tsx:L15-L25
EVIDENCE: src/state/AppStateProvider.tsx:L42-L44
- Settings persistence key: `axl-bff-settings` in localStorage; token explicitly excluded.
EVIDENCE: src/hooks/useGitHubSettings.ts:L13-L20
EVIDENCE: src/hooks/useGitHubSettings.ts:L36-L40
EVIDENCE: src/hooks/useGitHubSettings.ts:L78-L84
- Legacy token-bearing key is migrated and dropped.
EVIDENCE: src/hooks/useGitHubSettings.ts:L46-L61

## 1.4 API boundaries {#api-boundaries}
- `VITE_AXL_API_BASE` is required in prod; dev fallback is localhost worker.
EVIDENCE: src/lib/api.ts:L13-L24
- Dispatch uses `X-AXL-Api-Key` header.
EVIDENCE: src/lib/api.ts:L124-L130
