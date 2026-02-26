import { useLanguage } from '@/hooks/useLanguage';

type Tab = 'status' | 'pipeline' | 'evidence' | 'arsenal' | 'forge' | 'settings';

interface TabBarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

const TAB_KEYS: { id: Tab; key: 'tabStatus' | 'tabPipeline' | 'tabEvidence' | 'tabArsenal' | 'tabForge' | 'tabSettings' }[] = [
  { id: 'status', key: 'tabStatus' },
  { id: 'pipeline', key: 'tabPipeline' },
  { id: 'evidence', key: 'tabEvidence' },
  { id: 'arsenal', key: 'tabArsenal' },
  { id: 'forge', key: 'tabForge' },
  { id: 'settings', key: 'tabSettings' },
];

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const { t } = useLanguage();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 flex items-stretch"
      style={{ height: 48, background: 'var(--bg-primary)', borderTop: '1px solid var(--border-default)' }}
    >
      {TAB_KEYS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className="flex-1 flex items-center justify-center"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)', fontWeight: isActive ? 600 : 400, transition: 'color 200ms ease-out', minHeight: 48 }}
          >
            {t(tab.key)}
          </button>
        );
      })}
    </nav>
  );
}

export type { Tab };
