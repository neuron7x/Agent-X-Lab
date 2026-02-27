# 00 System Overview {#system-overview}

## 0.1 Scope {#scope}
This document covers the UI runtime, test suites, and CI workflows in this repository.
EVIDENCE: src/main.tsx:L1-L9
EVIDENCE: src/App.tsx:L39-L63

## 0.2 Startup narrative (authoritative) {#startup-narrative}
1. The browser entrypoint initializes observability and mounts `<App />`.
EVIDENCE: src/main.tsx:L4-L9
2. `<App />` composes providers in fixed order: QueryClient → Tooltip → Language → AppState.
EVIDENCE: src/App.tsx:L40-L44
3. Routing is nested under `AppShell`, with route table for `/`, `/pipeline`, `/evidence`, `/arsenal`, `/forge`, `/settings`, and wildcard `*`.
EVIDENCE: src/App.tsx:L46-L56
4. Route modules are lazy-loaded from `src/modules/index.ts`.
EVIDENCE: src/modules/index.ts:L6-L13

## 0.3 Runtime control flow {#runtime-flow}
```text
main.tsx
  -> initObservability()
  -> render(App)
     -> providers
     -> BrowserRouter/Routes
     -> AppShell
     -> lazy route outlet
```
EVIDENCE: src/main.tsx:L4-L9
EVIDENCE: src/App.tsx:L46-L58
EVIDENCE: src/components/shell/AppShell.tsx:L112-L121

## 0.4 Safety boundaries {#safety-boundaries}
- Browser API access is routed through BFF client module.
EVIDENCE: src/lib/api.ts:L1-L7
- `src/lib/github.ts` is a re-export shim pointing to `api.ts` (no direct GitHub client there).
EVIDENCE: src/lib/github.ts:L1-L10
EVIDENCE: src/lib/github.ts:L12-L33
- Protected actions are explicitly gated by API-key presence policy.
EVIDENCE: src/components/axl/ProtectedAction.tsx:L33-L42
