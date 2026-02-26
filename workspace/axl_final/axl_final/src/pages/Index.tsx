import { useState, useEffect, useCallback } from 'react';
import { useGitHubSettings } from '@/hooks/useGitHubSettings';
import { useGitHubAPI } from '@/hooks/useGitHubAPI';
import { useArsenal } from '@/hooks/useArsenal';
import { TopBar } from '@/components/axl/TopBar';
import { TabBar } from '@/components/axl/TabBar';
import type { Tab } from '@/components/axl/TabBar';
import { HomeScreen } from '@/components/axl/HomeScreen';
import { PipelineScreen } from '@/components/axl/PipelineScreen';
import { EvidenceScreen } from '@/components/axl/EvidenceScreen';
import { ArsenalScreen } from '@/components/axl/ArsenalScreen';
import { SettingsScreen } from '@/components/axl/SettingsScreen';
import { ForgeScreen } from '@/components/axl/ForgeScreen';
import { ConnectRepository } from '@/components/axl/ConnectRepository';
import { ErrorBanner } from '@/components/axl/ErrorBanner';
import { ErrorBoundary } from '@/components/axl/ErrorBoundary';
import { SkeletonPanel } from '@/components/axl/SkeletonPanel';
import { BottomBar } from '@/components/axl/BottomBar';

const Index = () => {
  const [isDemoMode, setIsDemoMode] = useState<boolean>(
    () => sessionStorage.getItem('axl_demo_mode') === '1'
  );
  const [activeTab, setActiveTab] = useState<Tab>('status');

  useEffect(() => {
    sessionStorage.setItem('axl_demo_mode', isDemoMode ? '1' : '0');
  }, [isDemoMode]);

  const { settings, updateSettings, clearSettings, isConfigured, bffStatus, probeBff: _probeBff } = useGitHubSettings();

  const {
    vrData, gates, evidence, prs,
    connectionStatus, error, rateLimitReset,
    contractError, parseFailures, isLoading,
  } = useGitHubAPI(settings, isConfigured, isDemoMode);

  const arsenal = useArsenal(settings, isConfigured, isDemoMode);

  const handlePreviewDemo = useCallback(() => {
    setIsDemoMode(true);
  }, []);

  const handleExitDemo = useCallback(() => {
    setIsDemoMode(false);
    sessionStorage.removeItem('axl_demo_mode');
  }, []);

  // STRICT: owner+repo required AND bff reachable → otherwise Connect screen
  if (!isDemoMode && !isConfigured) {
    return (
      <ConnectRepository
        onConnect={(patch, _probe) => updateSettings(patch)}
        onPreviewDemo={handlePreviewDemo}
        bffStatus={bffStatus}
      />
    );
  }

  const showSkeleton = isLoading && !isDemoMode;

  return (
    <div className="flex flex-col" style={{ minHeight: '100vh', background: 'var(--bg-void)' }}>
      <TopBar
        repoName={settings.repo || 'Agent-X-Lab'}
        connectionStatus={isDemoMode ? 'DISCONNECTED' : connectionStatus}
        demoMode={isDemoMode}
        onSettingsClick={() => setActiveTab('settings')}
        rateLimitReset={rateLimitReset}
      />

      <ErrorBanner
        vrData={vrData}
        gates={gates}
        connectionStatus={connectionStatus}
        error={error}
        rateLimitReset={rateLimitReset}
        contractError={contractError}
      />

      {/* Screen content */}
      <div style={{ paddingTop: 48, paddingBottom: 56 }}>
        {activeTab === 'status' && (
          <ErrorBoundary panelName="SystemState">
            {showSkeleton && !vrData ? (
              <div style={{ padding: 24 }}><SkeletonPanel lines={5} /></div>
            ) : (
              <HomeScreen
                vrData={vrData}
                gates={gates}
                onViewPipeline={() => setActiveTab('pipeline')}
                onNavigateToArsenal={() => setActiveTab('arsenal')}
                contractError={contractError}
              />
            )}
          </ErrorBoundary>
        )}
        {activeTab === 'pipeline' && (
          <ErrorBoundary panelName="PipelineMonitor">
            {showSkeleton && gates.length === 0 ? (
              <div style={{ padding: 24 }}><SkeletonPanel lines={6} /></div>
            ) : (
              <PipelineScreen gates={gates} />
            )}
          </ErrorBoundary>
        )}
        {activeTab === 'evidence' && (
          <ErrorBoundary panelName="EvidenceFeed">
            {showSkeleton && evidence.length === 0 ? (
              <div style={{ padding: 24 }}><SkeletonPanel lines={4} /></div>
            ) : (
              <EvidenceScreen entries={evidence} prs={prs} parseFailures={parseFailures} />
            )}
          </ErrorBoundary>
        )}
        {activeTab === 'arsenal' && (
          <ErrorBoundary panelName="Arsenal">
            <ArsenalScreen prompts={arsenal.prompts} isLoading={arsenal.isLoading} />
          </ErrorBoundary>
        )}
        {activeTab === 'forge' && (
          <ErrorBoundary panelName="PromptForge">
            <ForgeScreen />
          </ErrorBoundary>
        )}
        {activeTab === 'settings' && (
          <SettingsScreen
            settings={settings}
            onUpdateSettings={(patch) => {
              updateSettings(patch);
              if (isDemoMode && patch.token) {
                setIsDemoMode(false);
                sessionStorage.removeItem('axl_demo_mode');
              }
            }}
            onClearSettings={() => {
              clearSettings();
              handleExitDemo();
            }}
            lastVerified={null}
            isDemoMode={isDemoMode}
            onExitDemo={handleExitDemo}
          />
        )}
      </div>

      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
};

export default Index;
