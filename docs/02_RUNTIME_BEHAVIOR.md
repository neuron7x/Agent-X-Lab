# 02 Runtime Behavior {#runtime-behavior}

## 2.1 First-load sequence {#first-load}
- Observability starts before first render.
EVIDENCE: src/main.tsx:L4-L9
- App creates query retry policy that disables retries for `UNAUTHORIZED` and `RATE_LIMITED` errors.
EVIDENCE: src/App.tsx:L23-L33

## 2.2 Route rendering pipeline {#route-render-pipeline}
- Router resolves nested route inside `AppShell`; unknown paths go to `NotFound`.
EVIDENCE: src/App.tsx:L48-L56
EVIDENCE: src/pages/NotFound.tsx:L12-L19
- Outlet rendering is wrapped with `ErrorBoundary` and `Suspense` fallback.
EVIDENCE: src/components/shell/AppShell.tsx:L112-L116

## 2.3 Demo mode behavior {#demo-mode}
- Auto demo is enabled when preference is `auto` and settings are not configured.
EVIDENCE: src/state/AppStateProvider.tsx:L30-L36
- In demo mode, `useGitHubAPI` returns mock payload and no live query state.
EVIDENCE: src/hooks/useGitHubAPI.ts:L134-L146
EVIDENCE: src/hooks/useGitHubAPI.ts:L225-L227
- Arsenal hook returns `MOCK_ARSENAL` when demo mode is enabled.
EVIDENCE: src/hooks/useArsenal.ts:L15-L21

## 2.4 Command palette behavior {#command-palette}
- Ctrl/Cmd+K toggles palette in shell.
EVIDENCE: src/components/shell/AppShell.tsx:L35-L43
- Palette contract: dialog role, aria-label, closes on Escape/backdrop.
EVIDENCE: src/components/shell/CommandPalette.tsx:L72-L77
EVIDENCE: src/components/shell/CommandPalette.tsx:L31-L37
- Unit and E2E tests enforce this behavior.
EVIDENCE: src/components/shell/CommandPalette.test.tsx:L24-L48
EVIDENCE: e2e/smoke.spec.ts:L54-L67

## 2.5 Forge behavior {#forge-behavior}
- Forge exposes providers `claude`, `gpt`, `n8n`.
EVIDENCE: src/components/axl/ForgeScreen.tsx:L20-L48
- Stream endpoints: `/ai/forge`, `/ai/forge/gpt`, `/ai/forge/n8n`.
EVIDENCE: src/lib/api.ts:L461-L468
EVIDENCE: src/lib/api.ts:L573-L577
EVIDENCE: src/lib/api.ts:L655-L662
