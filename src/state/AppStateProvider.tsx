/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
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

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => sessionStorage.getItem('axl_demo_mode') === '1');

  useEffect(() => {
    sessionStorage.setItem('axl_demo_mode', isDemoMode ? '1' : '0');
  }, [isDemoMode]);

  const settingsState = useGitHubSettings();
  const githubState = useGitHubAPI(settingsState.settings, settingsState.isConfigured, isDemoMode);
  const arsenalState = useArsenal(settingsState.settings, settingsState.isConfigured, isDemoMode);

  const setDemoMode = useCallback((enabled: boolean) => {
    setIsDemoMode(enabled);
    if (!enabled) {
      sessionStorage.removeItem('axl_demo_mode');
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
