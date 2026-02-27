/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, type ReactNode, useState } from 'react';
import { useGitHubSettings } from '@/hooks/useGitHubSettings';
import { useGitHubAPI } from '@/hooks/useGitHubAPI';
import { useArsenal } from '@/hooks/useArsenal';

export interface AppStateContextValue {
  isDemoMode: boolean;
  setDemoMode: (enabled: boolean) => void;
  settingsState: ReturnType<typeof useGitHubSettings>;
  githubState: ReturnType<typeof useGitHubAPI>;
  arsenalState: ReturnType<typeof useArsenal>;
}

const DEMO_MODE_KEY = 'axl_demo_mode';

type DemoPreference = 'auto' | 'on' | 'off';

function readDemoPreference(): DemoPreference {
  if (typeof window === 'undefined') return 'auto';
  const stored = window.sessionStorage.getItem(DEMO_MODE_KEY);
  if (stored === '1') return 'on';
  if (stored === '0') return 'off';
  return 'auto';
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [demoPreference, setDemoPreference] = useState<DemoPreference>(readDemoPreference);

  const settingsState = useGitHubSettings();
  const isDemoMode = demoPreference === 'on' || (demoPreference === 'auto' && !settingsState.isConfigured);

  const githubState = useGitHubAPI(settingsState.settings, settingsState.isConfigured, isDemoMode);
  const arsenalState = useArsenal(settingsState.settings, settingsState.isConfigured, isDemoMode);

  const setDemoMode = useCallback((enabled: boolean) => {
    const nextPreference: DemoPreference = enabled ? 'on' : 'off';
    setDemoPreference(nextPreference);

    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(DEMO_MODE_KEY, enabled ? '1' : '0');
    }
  }, []);

  const value = useMemo(
    () => ({ isDemoMode, setDemoMode, settingsState, githubState, arsenalState }),
    [arsenalState, githubState, isDemoMode, setDemoMode, settingsState],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
