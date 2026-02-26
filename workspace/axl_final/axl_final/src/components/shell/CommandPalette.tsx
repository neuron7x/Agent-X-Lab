/**
 * CommandPalette — Cmd+K global command palette.
 * Uses cmdk (already in deps).
 * I5: keyboard accessible, focus managed, ARIA labelled.
 */
import { useEffect, useCallback, useRef } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useLanguage } from '@/hooks/useLanguage';
import { QK } from '@/lib/queryKeys';
import { dispatchRunEngine } from '@/lib/api';
import { useActionGate } from '@/components/axl/ProtectedAction';
import { log } from '@/lib/observability';

interface Props {
  onClose: () => void;
}

export function CommandPalette({ onClose }: Props) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { lang, setLang } = useLanguage();
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const go = useCallback((path: string) => {
    navigate(path);
    onClose();
  }, [navigate, onClose]);

  const invalidateAll = useCallback(() => {
    qc.invalidateQueries();
    onClose();
  }, [qc, onClose]);

  const { isAllowed } = useActionGate();

  const dispatchEngine = useCallback(async () => {
    if (!isAllowed) return;
    try {
      await dispatchRunEngine({ source: 'command-palette' });
      log.info('command-palette: engine dispatched');
    } catch (err) {
      log.error('command-palette: dispatch failed', { err: String(err) });
    }
    onClose();
  }, [isAllowed, onClose]);

  const NAV = [
    { label: lang === 'ua' ? 'Статус / Головна' : 'Status / Home', path: '/' },
    { label: lang === 'ua' ? 'Пайплайн' : 'Pipeline', path: '/pipeline' },
    { label: lang === 'ua' ? 'Докази' : 'Evidence', path: '/evidence' },
    { label: lang === 'ua' ? 'Промпт-арсенал' : 'Arsenal', path: '/arsenal' },
    { label: lang === 'ua' ? 'Кузня (Forge)' : 'Prompt Forge', path: '/forge' },
    { label: lang === 'ua' ? 'Налаштування' : 'Settings', path: '/settings' },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-[var(--bg-elevated,#111)] border border-[var(--border-dim,#333)] rounded-lg shadow-2xl overflow-hidden">
        <Command
          className="flex flex-col"
          onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
        >
          <div className="flex items-center border-b border-[var(--border-dim,#333)] px-3">
            <span className="text-[var(--text-dim,#666)] mr-2 text-xs">⌘K</span>
            <Command.Input
              ref={inputRef}
              placeholder={lang === 'ua' ? 'Команда або навігація…' : 'Command or navigate…'}
              className="flex-1 bg-transparent outline-none py-3 text-sm text-[var(--text-primary,#fff)] placeholder:text-[var(--text-dim,#666)]"
            />
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-xs text-[var(--text-dim,#666)]">
              {lang === 'ua' ? 'Нічого не знайдено' : 'No results found'}
            </Command.Empty>

            <Command.Group heading={<span className="text-[9px] font-bold tracking-widest text-[var(--text-dim,#666)] px-2 py-1 block">{lang === 'ua' ? 'НАВІГАЦІЯ' : 'NAVIGATE'}</span>}>
              {NAV.map(item => (
                <Command.Item
                  key={item.path}
                  value={item.label}
                  onSelect={() => go(item.path)}
                  className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[var(--text-primary,#fff)] cursor-pointer aria-selected:bg-[var(--bg-quaternary,#222)] hover:bg-[var(--bg-quaternary,#222)]"
                >
                  <span className="text-[var(--text-dim,#666)]">→</span>
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Group heading={<span className="text-[9px] font-bold tracking-widest text-[var(--text-dim,#666)] px-2 py-1 block">{lang === 'ua' ? 'ДІЇ' : 'ACTIONS'}</span>}>
              <Command.Item
                value={lang === 'ua' ? 'Оновити всі дані' : 'Refresh all data'}
                onSelect={invalidateAll}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[var(--text-primary,#fff)] cursor-pointer aria-selected:bg-[var(--bg-quaternary,#222)] hover:bg-[var(--bg-quaternary,#222)]"
              >
                <span className="text-[var(--text-dim,#666)]">↺</span>
                {lang === 'ua' ? 'Оновити всі дані' : 'Refresh all data'}
              </Command.Item>
              <Command.Item
                value={lang === 'ua' ? 'Змінити мову' : 'Toggle language UA/EN'}
                onSelect={() => { setLang(lang === 'ua' ? 'en' : 'ua'); onClose(); }}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[var(--text-primary,#fff)] cursor-pointer aria-selected:bg-[var(--bg-quaternary,#222)] hover:bg-[var(--bg-quaternary,#222)]"
              >
                <span className="text-[var(--text-dim,#666)]">🌐</span>
                {lang === 'ua' ? 'UA → EN' : 'EN → UA'}
              </Command.Item>
              {isAllowed && (
                <Command.Item
                  value={lang === 'ua' ? 'Запустити Engine' : 'Dispatch Engine run'}
                  onSelect={dispatchEngine}
                  className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[var(--text-primary,#fff)] cursor-pointer aria-selected:bg-[var(--bg-quaternary,#222)] hover:bg-[var(--bg-quaternary,#222)]"
                >
                  <span className="text-[var(--signal-pass,#00e87a)]">▶</span>
                  {lang === 'ua' ? 'Запустити Engine' : 'Dispatch Engine run'}
                </Command.Item>
              )}
              <Command.Item
                value={lang === 'ua' ? 'Перейти до доказів' : 'Go to latest evidence'}
                onSelect={() => go('/evidence')}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm text-[var(--text-primary,#fff)] cursor-pointer aria-selected:bg-[var(--bg-quaternary,#222)] hover:bg-[var(--bg-quaternary,#222)]"
              >
                <span className="text-[var(--text-dim,#666)]">📋</span>
                {lang === 'ua' ? 'Останні докази' : 'Latest evidence'}
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="border-t border-[var(--border-dim,#333)] px-3 py-2 flex gap-3 text-[9px] text-[var(--text-dim,#666)]">
            <span>↑↓ навігація</span>
            <span>↵ вибрати</span>
            <span>Esc закрити</span>
          </div>
        </Command>
      </div>
    </div>
  );
}
