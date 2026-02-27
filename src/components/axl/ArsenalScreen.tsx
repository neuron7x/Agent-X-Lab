import { useState, useCallback, useMemo } from 'react';
import type { ArsenalPrompt, ArsenalRole } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import type { Lang } from '@/lib/i18n';

// ── Prompt section parser ──

interface PromptSection {
  label: string;
  labelColor: string;
  content: string;
}

function parsePromptSections(content: string, lang: Lang): { sections: PromptSection[]; fullText: string } {
  const sectionPatterns: { pattern: RegExp; label: { ua: string; en: string }; color: string }[] = [
    { pattern: /(?:^|\n)(MISSION|PRIMARY OBJECTIVE|OPERATING MODEL.*?)\n([\s\S]*?)(?=\n(?:HARD PRINCIPLES|INVARIANTS|FAIL-CLOSED|NON-NEGOTIABLE|GATE MATRIX|REQUIRED|SCOPE|OUTPUT|STOP|FINAL|$))/i,
      label: { ua: 'АЛГОРИТМ', en: 'ALGORITHM' }, color: '#0a84ff' },
    { pattern: /(?:^|\n)(HARD PRINCIPLES.*?|INVARIANTS.*?|NON-NEGOTIABLE INVARIANTS.*?|FAIL-CLOSED PRINCIPLES.*?)\n([\s\S]*?)(?=\n(?:SCOPE|GATE|REQUIRED|OUTPUT|OPERATING|STEP|STOP|FINAL|$))/i,
      label: { ua: 'ОБМЕЖЕННЯ', en: 'CONSTRAINTS' }, color: '#ff3b30' },
    { pattern: /(?:^|\n)(FINAL OUTPUT.*?|FINAL CHAT OUTPUT.*?|FINAL RULE.*?|STOP CONDITIONS.*?|OUTPUT TEMPLATE.*?)\n([\s\S]*?)(?=\n(?:END OF|$))/i,
      label: { ua: 'ОЧІКУВАНИЙ РЕЗУЛЬТАТ', en: 'EXPECTED OUTPUT' }, color: '#00e87a' },
  ];

  const sections: PromptSection[] = [];
  for (const sp of sectionPatterns) {
    const match = content.match(sp.pattern);
    if (match) {
      const header = match[1].trim();
      const body = match[2].trim();
      sections.push({
        label: sp.label[lang],
        labelColor: sp.color,
        content: header + '\n' + body,
      });
    }
  }

  return { sections, fullText: content };
}

interface ArsenalScreenProps {
  prompts: ArsenalPrompt[];
  isLoading: boolean;
}

type ArsenalView =
  | { level: 'clusters' }
  | { level: 'platforms'; role: ArsenalRole }
  | { level: 'prompts'; role: ArsenalRole; target: string; selectedId: string | null };

const ROLE_COLORS: Record<ArsenalRole, string> = {
  'PR-AGENT': '#0a84ff',
  'CI-AGENT': '#ff9f0a',
  'DOCS-AGENT': '#ffffff',
  'SCIENCE-AGENT': '#aa66ff',
  'SECURITY-AGENT': '#ff3b30',
  'OTHER': '#444444',
};

// ── Cluster metadata ──

interface ClusterMeta {
  name: string;
  topic: { ua: string; en: string };
  goal: { ua: string; en: string };
  accent: string;
}

const CLUSTER_META: Record<string, ClusterMeta> = {
  'PR-AGENT': {
    name: 'PR-AGENT',
    topic: { ua: 'Керування репозиторієм', en: 'Repository Management' },
    goal: { ua: 'Автоматизація PR та CI-гейтів', en: 'PR automation and CI gate enforcement' },
    accent: '#0a84ff',
  },
  'CI-AGENT': {
    name: 'CI-AGENT',
    topic: { ua: 'Надійність тестів', en: 'Test Reliability' },
    goal: { ua: 'Усунення нестабільних тестів', en: 'Flake elimination and test stability' },
    accent: '#ff9f0a',
  },
  'DOCS-AGENT': {
    name: 'DOCS-AGENT',
    topic: { ua: 'Документація та онбординг', en: 'Documentation and Onboarding' },
    goal: { ua: 'Запуск проєкту за 5 хвилин', en: 'Project onboarding under 5 minutes' },
    accent: '#ffffff',
  },
  'SCIENCE-AGENT': {
    name: 'SCIENCE-AGENT',
    topic: { ua: 'Наукова симуляція', en: 'Scientific Simulation' },
    goal: { ua: 'Відтворювані дослідницькі артефакти', en: 'Reproducible research artifacts' },
    accent: '#aa66ff',
  },
  'SECURITY-AGENT': {
    name: 'SECURITY-AGENT',
    topic: { ua: 'Верифікація та безпека', en: 'Verification and Security' },
    goal: { ua: 'Досконалість якості та захист ланцюга постачання', en: 'Quality perfection and supply chain security' },
    accent: '#ff3b30',
  },
  'ALL': {
    name: 'ALL',
    topic: { ua: 'Всі протоколи', en: 'All protocols' },
    goal: { ua: 'Повний арсенал агентів', en: 'Complete agent arsenal' },
    accent: '#444444',
  },
};

// ── Platform sub-category metadata ──

interface PlatformMeta {
  goal: { ua: string; en: string };
}

const PLATFORM_META: Record<string, Record<string, PlatformMeta>> = {
  'PR-AGENT': {
    'Codex / GitHub Copilot': { goal: { ua: 'Виконання PR через Codex Tasks', en: 'PR execution via Codex Tasks' } },
    'Claude / API': { goal: { ua: 'Архітектурний аудит через Claude', en: 'Architectural audit via Claude' } },
  },
  'CI-AGENT': {
    'GitHub Actions': { goal: { ua: 'CI pipeline та gate enforcement', en: 'CI pipeline and gate enforcement' } },
    'Codex': { goal: { ua: 'Автономне виправлення тестів', en: 'Autonomous test fixes' } },
  },
  'DOCS-AGENT': {
    'Codex / GitHub Copilot': { goal: { ua: 'Генерація документації через Codex', en: 'Documentation generation via Codex' } },
  },
  'SCIENCE-AGENT': {
    'Codex / Claude': { goal: { ua: 'Наукова симуляція та proof artifacts', en: 'Scientific simulation and proof artifacts' } },
    'Gemini': { goal: { ua: 'Оцінка стану репозиторію', en: 'Repository health assessment' } },
  },
  'SECURITY-AGENT': {
    'Codex / Claude': { goal: { ua: 'Верифікація + security hardening', en: 'Verification + security hardening' } },
  },
};

const MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

export function ArsenalScreen({ prompts, isLoading }: ArsenalScreenProps) {
  const { t, lang } = useLanguage();
  const [view, setView] = useState<ArsenalView>({ level: 'clusters' });
  const [copied, setCopied] = useState(false);

  // Group prompts by role
  const clusters = useMemo(() => {
    const map = new Map<ArsenalRole, ArsenalPrompt[]>();
    for (const p of prompts) {
      const list = map.get(p.role) || [];
      list.push(p);
      map.set(p.role, list);
    }
    return map;
  }, [prompts]);

  // Get unique targets for a role
  const getTargets = useCallback((role: ArsenalRole) => {
    const rolePrompts = clusters.get(role) || [];
    const targets = new Map<string, number>();
    for (const p of rolePrompts) {
      targets.set(p.target, (targets.get(p.target) || 0) + 1);
    }
    return targets;
  }, [clusters]);

  const handleCopy = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 104px)' }}>
        <span className="axl-label">LOADING...</span>
      </div>
    );
  }

  // ── Breadcrumb ──
  const renderBreadcrumb = () => {
    if (view.level === 'clusters') return null;
    const accent = ROLE_COLORS[view.role];
    return (
      <div className="flex items-center gap-2" style={{ marginBottom: 20 }}>
        <CrumbBtn label={t('arsenalTitle')} onClick={() => setView({ level: 'clusters' })} />
        {(view.level === 'platforms' || view.level === 'prompts') && (
          <>
            <span style={{ fontSize: 10, color: '#333333', fontFamily: MONO }}>→</span>
            <CrumbBtn
              label={view.role}
              color={accent}
              onClick={() => setView({ level: 'platforms', role: view.role })}
            />
          </>
        )}
        {view.level === 'prompts' && (
          <>
            <span style={{ fontSize: 10, color: '#333333', fontFamily: MONO }}>→</span>
            <CrumbBtn label={view.target} />
          </>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════════
  // LEVEL 1 — CLUSTER CARDS
  // ═══════════════════════════════════════════
  if (view.level === 'clusters') {
    const roles = Array.from(clusters.keys());
    const totalCount = prompts.length;
    return (
      <div style={{ padding: 'var(--space-lg)' }}>
        <div className="axl-label" style={{ marginBottom: 24, fontSize: 11, letterSpacing: '0.14em' }}>
          {t('arsenalTitle')}
        </div>
        {roles.length === 0 ? (
          <div className="flex items-center justify-center" style={{ minHeight: 200 }}>
            <span className="axl-label">{t('arsenalNoData')}</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {roles.map(role => {
              const meta = CLUSTER_META[role] || CLUSTER_META['ALL'];
              const count = clusters.get(role)?.length || 0;
              return (
                <NavCard
                  key={role}
                  name={role}
                  topic={meta.topic[lang]}
                  goal={meta.goal[lang]}
                  accent={meta.accent}
                  count={count}
                  protocolsLabel={t('arsenalProtocols')}
                  onClick={() => setView({ level: 'platforms', role })}
                />
              );
            })}
            {/* ALL card — always last */}
            <NavCard
              name="ALL"
              topic={CLUSTER_META['ALL'].topic[lang]}
              goal={CLUSTER_META['ALL'].goal[lang]}
              accent={CLUSTER_META['ALL'].accent}
              count={totalCount}
              protocolsLabel={t('arsenalProtocols')}
              onClick={() => setView({ level: 'prompts', role: 'OTHER' as ArsenalRole, target: '__ALL__', selectedId: null })}
            />
          </div>
        )}
      </div>
    );
  }

  // ═══════════════════════════════════════════
  // LEVEL 2 — PLATFORM SUB-CATEGORIES
  // ═══════════════════════════════════════════
  if (view.level === 'platforms') {
    const targets = getTargets(view.role);
    const accent = ROLE_COLORS[view.role];
    const platformMeta = PLATFORM_META[view.role] || {};
    return (
      <div style={{ padding: 'var(--space-lg)' }}>
        {renderBreadcrumb()}
        {targets.size === 0 ? (
          <div className="flex items-center justify-center" style={{ minHeight: 200 }}>
            <span style={{ fontSize: 12, color: '#333333', fontFamily: MONO }}>{t('arsenalNoData')}</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {Array.from(targets.entries()).map(([target, count]) => {
              const pm = platformMeta[target];
              return (
                <NavCard
                  key={target}
                  name={target}
                  topic=""
                  goal={pm ? pm.goal[lang] : ''}
                  accent={accent}
                  count={count}
                  protocolsLabel={t('arsenalProtocols')}
                  onClick={() => setView({ level: 'prompts', role: view.role, target, selectedId: null })}
                />
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ═══════════════════════════════════════════
  // LEVEL 3 — PROMPT LIST + VIEWER
  // ═══════════════════════════════════════════
  const isAllView = view.target === '__ALL__';
  const levelPrompts = isAllView ? prompts : (clusters.get(view.role) || []).filter(p => p.target === view.target);
  const selected = levelPrompts.find(p => p.id === view.selectedId) || null;
  const accent = isAllView ? '#444444' : ROLE_COLORS[view.role];

  return (
    <div style={{ padding: 'var(--space-lg)' }}>
      {/* Breadcrumb for ALL view */}
      {isAllView ? (
        <div className="flex items-center gap-2" style={{ marginBottom: 20 }}>
          <CrumbBtn label={t('arsenalTitle')} onClick={() => setView({ level: 'clusters' })} />
          <span style={{ fontSize: 10, color: '#333333', fontFamily: MONO }}>→</span>
          <CrumbBtn label="ALL" />
        </div>
      ) : renderBreadcrumb()}

      <div className="flex gap-4" style={{ minHeight: 'calc(100vh - 200px)' }}>
        {/* Left panel — prompt list */}
        <div
          className="axl-panel flex flex-col"
          style={{ width: 260, flexShrink: 0, overflow: 'hidden' }}
        >
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {levelPrompts.map(prompt => {
              const isActive = selected?.id === prompt.id;
              return (
                <button
                  key={prompt.id}
                  onClick={() => setView({ ...view, selectedId: prompt.id })}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '12px 14px',
                    background: isActive ? '#0c0c0c' : 'transparent',
                    border: 'none',
                    borderLeft: isActive ? `1px solid ${accent}` : '1px solid transparent',
                    borderBottom: '1px solid #1c1c1c',
                    cursor: 'pointer',
                    transition: 'background 150ms ease-out',
                  }}
                >
                  <div style={{
                    fontSize: 11,
                    fontWeight: 500,
                    color: isActive ? '#ffffff' : '#666666',
                    marginBottom: 4,
                    fontFamily: MONO,
                    lineHeight: 1.4,
                  }}>
                    {prompt.title}
                  </div>
                  <div style={{ fontSize: 9, color: '#333333', fontFamily: MONO }}>
                    v{prompt.version}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right panel — detail viewer */}
        {selected ? (
          <div className="axl-panel flex-1 flex flex-col" style={{ overflow: 'hidden', position: 'relative' }}>
            {/* Top section */}
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #1c1c1c', flexShrink: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#ffffff', marginBottom: 4, fontFamily: MONO }}>
                {selected.title}
              </div>
              <div style={{ fontSize: 10, color: '#666666', marginBottom: 2, fontFamily: MONO }}>
                {CLUSTER_META[selected.role]?.topic[lang] || ''}
              </div>
              <div style={{ fontSize: 9, color: '#444444', marginBottom: 8, fontFamily: MONO }}>
                {CLUSTER_META[selected.role]?.goal[lang] || ''}
              </div>
              <div className="flex items-center gap-3" style={{ fontSize: 9, color: '#333333', fontFamily: MONO }}>
                <span>v{selected.version}</span>
                <span>•</span>
                <span>{selected.target}</span>
                <span>•</span>
                <span>{selected.sha}</span>
              </div>
            </div>

            {/* Structured sections */}
            <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 56 }}>
              <PromptSections content={selected.content} lang={lang} />

              {/* Full text */}
              <div style={{ padding: '20px' }}>
                <pre style={{
                  fontSize: 11,
                  lineHeight: 1.7,
                  color: '#777777',
                  fontFamily: MONO,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                }}>
                  {selected.content}
                </pre>
              </div>
            </div>

            {/* Bottom bar */}
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: 44,
              padding: '0 20px',
              borderTop: '1px solid #1c1c1c',
              background: 'var(--bg-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 10, color: '#333333', fontFamily: MONO }}>
                {selected.sha}
              </span>
              <button
                onClick={() => handleCopy(selected.content)}
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  padding: '4px 16px',
                  borderRadius: 999,
                  cursor: 'pointer',
                  letterSpacing: '0.06em',
                  border: `1px solid ${copied ? accent : '#1c1c1c'}`,
                  background: 'transparent',
                  color: copied ? accent : '#555555',
                  transition: 'all 200ms ease-out',
                  fontFamily: MONO,
                }}
                onMouseEnter={(e) => {
                  if (!copied) { e.currentTarget.style.borderColor = '#ffffff'; e.currentTarget.style.color = '#ffffff'; }
                }}
                onMouseLeave={(e) => {
                  if (!copied) { e.currentTarget.style.borderColor = '#1c1c1c'; e.currentTarget.style.color = '#555555'; }
                }}
              >
                {copied ? t('arsenalCopied') : t('arsenalCopy')}
              </button>
            </div>
          </div>
        ) : (
          <div className="axl-panel flex-1 flex items-center justify-center">
            <span style={{ fontSize: 11, color: '#333333', letterSpacing: '0.1em', fontFamily: MONO }}>
              {t('arsenalEmpty')}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Reusable components ──

function NavCard({ name, topic, goal, accent, count, protocolsLabel: _protocolsLabel, onClick }: {
  name: string; topic: string; goal: string; accent: string;
  count: number; protocolsLabel: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        minHeight: 120,
        padding: '16px',
        background: '#0a0a0a',
        border: '1px solid #1c1c1c',
        borderRadius: 2,
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'border-color 150ms ease-out',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = accent; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#1c1c1c'; }}
    >
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: accent, marginBottom: 6, fontFamily: MONO }}>
          {name}
        </div>
        {topic && (
          <div style={{ fontSize: 10, color: '#666666', marginBottom: 4, fontFamily: MONO }}>
            {topic}
          </div>
        )}
        {goal && (
          <div style={{ fontSize: 9, color: '#444444', fontFamily: MONO, lineHeight: 1.4 }}>
            {goal}
          </div>
        )}
      </div>
      <div style={{
        fontSize: 10, color: '#444444', fontFamily: MONO,
        alignSelf: 'flex-end', marginTop: 8,
      }}>
        {count} →
      </div>
    </button>
  );
}

function CrumbBtn({ label, onClick, color }: { label: string; onClick?: () => void; color?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      style={{
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.06em',
        color: color || (onClick ? '#888888' : '#555555'),
        background: 'none',
        border: 'none',
        cursor: onClick ? 'pointer' : 'default',
        padding: 0,
        fontFamily: MONO,
      }}
    >
      {label}
    </button>
  );
}

// ── Prompt structured sections ──

function PromptSections({ content, lang }: { content: string; lang: Lang }) {
  const { sections } = parsePromptSections(content, lang);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  if (sections.length === 0) return null;

  return (
    <div style={{ padding: '12px 20px 0', borderBottom: '1px solid #1c1c1c' }}>
      {sections.map((sec) => {
        const isOpen = expanded[sec.label] || false;
        return (
          <div key={sec.label} style={{ marginBottom: 12 }}>
            <button
              onClick={() => setExpanded(prev => ({ ...prev, [sec.label]: !isOpen }))}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
                width: '100%',
              }}
            >
              <span style={{ fontSize: 9, color: '#333333', fontFamily: MONO }}>
                {isOpen ? '▼' : '▶'}
              </span>
              <span style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: '0.1em',
                color: sec.labelColor,
                fontFamily: MONO,
              }}>
                {sec.label}
              </span>
            </button>
            {isOpen && (
              <pre style={{
                fontSize: 10,
                lineHeight: 1.6,
                color: '#666666',
                fontFamily: MONO,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: '8px 0 0 17px',
                padding: 0,
              }}>
                {sec.content}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
}
