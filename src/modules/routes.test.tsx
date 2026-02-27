import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { StatusRoute } from '@/modules/status/StatusRoute';
import { PipelineRoute } from '@/modules/pipeline/PipelineRoute';
import { EvidenceRoute } from '@/modules/evidence/EvidenceRoute';
import { ArsenalRoute } from '@/modules/arsenal/ArsenalRoute';
import { SettingsRoute } from '@/modules/settings/SettingsRoute';
import { AppShell } from '@/components/shell/AppShell';

vi.mock('@/state/AppStateProvider', () => ({
  useAppState: () => ({
    isDemoMode: true,
    setDemoMode: vi.fn(),
    settingsState: {
      settings: { token: '', owner: 'o', repo: 'r', pollInterval: 30 },
      updateSettings: vi.fn(),
      clearSettings: vi.fn(),
      isConfigured: true,
      bffStatus: 'REACHABLE',
      probeBff: vi.fn(),
    },
    githubState: {
      vrData: { status: 'RUN', metrics: {}, blockers: [] },
      gates: [{ id: 'lint', status: 'PASS', tool: 'eslint', elapsed: '1s' }],
      evidence: [{ timestamp: '2026-01-01', type: 'gate', status: 'PASS', sha: 'abc12345' }],
      prs: [{ number: 1, title: 't', url: 'https://example.com', checksPassed: 1, checksTotal: 1 }],
      parseFailures: 0,
      contractError: null,
      connectionStatus: 'CONNECTED',
      error: null,
      rateLimitReset: null,
    },
    arsenalState: {
      prompts: [{ id: 'p1', title: 'Prompt', role: 'SYSTEM', category: 'CAT', content: 'Body', tags: [] }],
      isLoading: false,
      error: null,
    },
  }),
}));

vi.mock('@/components/axl/HomeScreen', () => ({ HomeScreen: () => <div>home-screen</div> }));
vi.mock('@/components/axl/PipelineScreen', () => ({ PipelineScreen: () => <div>pipeline-screen</div> }));
vi.mock('@/components/axl/EvidenceScreen', () => ({ EvidenceScreen: () => <div>evidence-screen</div> }));
vi.mock('@/components/axl/ArsenalScreen', () => ({ ArsenalScreen: () => <div>arsenal-screen</div> }));
vi.mock('@/components/axl/SettingsScreen', () => ({ SettingsScreen: () => <div>settings-screen</div> }));

describe('route containers', () => {
  it('renders status route container', () => {
    render(<MemoryRouter><StatusRoute /></MemoryRouter>);
    expect(screen.getByText('home-screen')).toBeInTheDocument();
  });

  it('renders pipeline route container', () => {
    render(<PipelineRoute />);
    expect(screen.getByText('pipeline-screen')).toBeInTheDocument();
  });

  it('renders evidence route container', () => {
    render(<EvidenceRoute />);
    expect(screen.getByText('evidence-screen')).toBeInTheDocument();
  });

  it('renders arsenal route container', () => {
    render(<ArsenalRoute />);
    expect(screen.getByText('arsenal-screen')).toBeInTheDocument();
  });

  it('renders settings route container', () => {
    render(<SettingsRoute />);
    expect(screen.getByText('settings-screen')).toBeInTheDocument();
  });

  it('renders app shell landmarks and skip link', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<div>index-content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute('href', '#main-content');
  });
});
