/**
 * AppShell — root layout for all routes.
 * Replaces tab-state in Index.tsx with React Router routes.
 * Provides: nav, error boundary per outlet, skip-to-content (a11y).
 */
import { Suspense, useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ErrorBoundary } from '@/components/axl/ErrorBoundary';
import { SkeletonPanel } from '@/components/axl/SkeletonPanel';
import { TopBar } from '@/components/axl/TopBar';
import { CommandPalette } from '@/components/shell/CommandPalette';
import { useLanguage } from '@/hooks/useLanguage';
import { cn } from '@/lib/utils';
import { VersionStamp } from '@/components/axl/VersionStamp';
import { useAppState } from '@/state/AppStateProvider';
import { ConnectRepository } from '@/components/axl/ConnectRepository';
import { ErrorBanner } from '@/components/axl/ErrorBanner';

export const ROUTES = [
  { path: '/', labelUa: 'СТАТУС', labelEn: 'STATUS' },
  { path: '/pipeline', labelUa: 'ПАЙПЛАЙН', labelEn: 'PIPELINE' },
  { path: '/evidence', labelUa: 'ДОКАЗИ', labelEn: 'EVIDENCE' },
  { path: '/arsenal', labelUa: 'ПРОМПТ', labelEn: 'PROMPT' },
  { path: '/forge', labelUa: 'КУЗНЯ', labelEn: 'FORGE' },
  { path: '/settings', labelUa: 'НАЛАШ.', labelEn: 'SETTINGS' },
] as const;

export function AppShell() {
  const navigate = useNavigate();
  const { lang, t } = useLanguage();
  const [cmdOpen, setCmdOpen] = useState(false);
  const { isDemoMode, setDemoMode, settingsState, githubState } = useAppState();

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

  if (!isDemoMode && !settingsState.isConfigured) {
    return (
      <ConnectRepository
        onConnect={(patch) => settingsState.updateSettings(patch)}
        onPreviewDemo={() => setDemoMode(true)}
        bffStatus={settingsState.bffStatus}
      />
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:bg-background focus:border focus:border-border focus:rounded focus:text-foreground"
      >
        {t('skipToMain')}
      </a>

      <TopBar
        repoName={settingsState.settings.repo || 'Agent-X-Lab'}
        connectionStatus={isDemoMode ? 'DISCONNECTED' : githubState.connectionStatus}
        demoMode={isDemoMode}
        onSettingsClick={() => navigate('/settings')}
        onOpenCommandPalette={() => setCmdOpen(true)}
        rateLimitReset={githubState.rateLimitReset}
      />

      <ErrorBanner
        vrData={githubState.vrData}
        gates={githubState.gates}
        connectionStatus={githubState.connectionStatus}
        error={githubState.error}
        rateLimitReset={githubState.rateLimitReset}
        contractError={githubState.contractError}
      />

      <nav aria-label={t('mainNavigation')} className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 backdrop-blur-sm supports-[backdrop-filter]:bg-background/80 relative">
        <ul className="flex h-12">
          {ROUTES.map(route => (
            <li key={route.path} className="flex-1">
              <NavLink
                to={route.path}
                end={route.path === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex h-full w-full items-center justify-center text-xs font-bold tracking-widest transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
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
        <div className="absolute right-2 bottom-0 h-12 flex items-center pointer-events-none">
          <VersionStamp compact />
        </div>
      </nav>

      <main id="main-content" className="flex-1 pb-12 overflow-y-auto" tabIndex={-1}>
        <ErrorBoundary panelName="AppShell">
          <Suspense fallback={<SkeletonPanel />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>

      {cmdOpen && <CommandPalette onClose={() => setCmdOpen(false)} />}
    </div>
  );
}
