import { SettingsScreen } from '@/components/axl/SettingsScreen';
import { useAppState } from '@/state/AppStateProvider';

export function SettingsRoute() {
  const { isDemoMode, setDemoMode, settingsState } = useAppState();

  return (
    <SettingsScreen
      settings={settingsState.settings}
      onUpdateSettings={settingsState.updateSettings}
      onClearSettings={() => {
        settingsState.clearSettings();
        setDemoMode(false);
      }}
      lastVerified={null}
      isDemoMode={isDemoMode}
      onExitDemo={() => setDemoMode(false)}
    />
  );
}
