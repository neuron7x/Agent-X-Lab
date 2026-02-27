/**
 * AppShell — root layout for all routes.
 * Replaces tab-state in Index.tsx with React Router routes.
 * Provides: nav, error boundary per outlet, skip-to-content (a11y).
 */
import { Suspense, useEffect, useRef, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { ErrorBoundary } from '@/components/axl/ErrorBoundary';
import { SkeletonPanel } from '@/components/axl/SkeletonPanel';
import { TopBar } from '@/components/axl/TopBar';
import { CommandPalette } from '@/components/shell/CommandPalette';
import { useLanguage } from '@/hooks/useLanguage';
import { cn } from '@/lib/utils';
import { VersionStamp } from '@/components/axl/VersionStamp';

// ── Route meta ─────────────────────────────────────────────────────────────
export const ROUTES = [
  { path: '/',         key: 'navStatus',   labelUa: 'СТАТУС',   labelEn: 'STATUS'   },
  { path: '/pipeline', key: 'navPipeline', labelUa: 'ПАЙПЛАЙН', labelEn: 'PIPELINE' },
  { path: '/evidence', key: 'navEvidence', labelUa: 'ДОКАЗИ',   labelEn: 'EVIDENCE' },
  { path: '/arsenal',  key: 'navArsenal',  labelUa: 'ПРОМПТ',   labelEn: 'PROMPT'   },
  { path: '/forge',    key: 'navForge',    labelUa: 'КУЗНЯ',    labelEn: 'FORGE'    },
  { path: '/settings', key: 'navSettings', labelUa: 'НАЛАШ.',   labelEn: 'SETTINGS' },
] as const;

// ── Shell ──────────────────────────────────────────────────────────────────
export function AppShell() {
  const { lang } = useLanguage();
  const [cmdOpen, setCmdOpen] = useState(false);
  const skipRef = useRef<HTMLAnchorElement>(null);

  // Keyboard shortcut: Cmd/Ctrl+K → command palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(v => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      {/* Skip to content — a11y */}
      <a
        ref={skipRef}
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:bg-background focus:border focus:border-border focus:rounded focus:text-foreground"
      >
        Skip to main content
      </a>

      {/* Top bar */}
      <TopBar onOpenCommandPalette={() => setCmdOpen(true)} />

      {/* Bottom nav */}
      <nav aria-label="Main navigation" className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 backdrop-blur-sm supports-[backdrop-filter]:bg-background/80 relative">
        <ul className="flex h-12">
          {ROUTES.map(route => (
            <li key={route.path} className="flex-1">
              <NavLink
                to={route.path}
                end={route.path === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex h-full w-full items-center justify-center text-[9px] font-bold tracking-widest transition-colors',
                    isActive
                      ? 'text-foreground border-t-2 border-foreground'
                      : 'text-muted-foreground hover:text-foreground border-t-2 border-transparent'
                  )
                }
              >
                {lang === 'ua' ? route.labelUa : route.labelEn}
              </NavLink>
            </li>
          ))}
        </ul>
        {/* Version stamp — Phase 8.3: releases traceable */}
        <div className="absolute right-2 bottom-0 h-12 flex items-center pointer-events-none">
          <VersionStamp compact />
        </div>
      </nav>

      {/* Main content */}
      <main
        id="main-content"
        className="flex-1 pb-12 overflow-y-auto"
        tabIndex={-1}
      >
        <ErrorBoundary panelName="AppShell">
          <Suspense fallback={<SkeletonPanel />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>

      {/* Command palette */}
      {cmdOpen && <CommandPalette onClose={() => setCmdOpen(false)} />}
    </div>
  );
}
