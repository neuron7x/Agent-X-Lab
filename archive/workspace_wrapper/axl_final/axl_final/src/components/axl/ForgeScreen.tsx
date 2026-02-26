/**
 * ForgeScreen — Prompt Forge UI
 * Підтримує 3 провайдери: Claude (Anthropic) | GPT-5.2 (OpenAI) | n8n
 *
 * Flow:
 *   User описує задачу → вибирає провайдера + режим (single/bundle)
 *   → POST /ai/forge | /ai/forge/gpt | /ai/forge/n8n (через BFF Worker)
 *   → SSE streaming → рендер результату з Copy кнопкою
 *
 * SECURITY: нульових токенів в браузері. Всі ключі (ANTHROPIC_API_KEY,
 * OPENAI_API_KEY, N8N_SECRET) живуть виключно в Cloudflare Worker secrets.
 */
import { useState, useRef, useCallback } from 'react';
import { forgeStream, forgeStreamGPT, forgeStreamN8n } from '@/lib/api';
import type { ForgeMode, ForgeMessage, ForgeStreamCallbacks } from '@/lib/api';
import type { ForgeProvider } from '@/lib/api';

// ── Provider config ────────────────────────────────────────────────────────

const PROVIDERS: Array<{
  id: ForgeProvider;
  label: string;
  sublabel: string;
  color: string;
  badge: string;
}> = [
  {
    id: 'claude',
    label: 'CLAUDE',
    sublabel: 'claude-sonnet-4-6',
    color: '#c77dff',
    badge: 'Anthropic',
  },
  {
    id: 'gpt',
    label: 'GPT-5.2',
    sublabel: 'gpt-5.2',
    color: '#00e87a',
    badge: 'OpenAI',
  },
  {
    id: 'n8n',
    label: 'N8N',
    sublabel: 'workflow routing',
    color: '#ff6b35',
    badge: 'n8n.io',
  },
];

// ── Component ──────────────────────────────────────────────────────────────

export function ForgeScreen() {
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<ForgeProvider>('claude');
  const [mode, setMode] = useState<ForgeMode>('single');
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState<'idle' | 'streaming' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [copied, setCopied] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const outputRef = useRef('');

  const handleSubmit = useCallback(() => {
    if (!input.trim() || status === 'streaming') return;

    // Reset
    setOutput('');
    setErrorMsg('');
    setCopied(false);
    outputRef.current = '';
    setStatus('streaming');

    const messages: ForgeMessage[] = [{ role: 'user', content: input.trim() }];

    const callbacks: ForgeStreamCallbacks = {
      onToken: (token: string) => {
        outputRef.current += token;
        setOutput(outputRef.current);
      },
      onDone: () => setStatus('done'),
      onError: (err: string) => {
        setErrorMsg(err);
        setStatus('error');
      },
    };

    let ctrl: AbortController;
    if (provider === 'gpt') {
      ctrl = forgeStreamGPT(messages, mode, callbacks);
    } else if (provider === 'n8n') {
      ctrl = forgeStreamN8n(messages, mode, callbacks);
    } else {
      ctrl = forgeStream(messages, mode, 'claude-sonnet-4-6', callbacks);
    }

    abortRef.current = ctrl;
  }, [input, mode, provider, status]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setStatus('done');
  }, []);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(output).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [output]);

  const activeProvider = PROVIDERS.find(p => p.id === provider)!;

  const mono = "'JetBrains Mono', monospace";

  return (
    <div style={{ padding: 'var(--space-xl)', maxWidth: 720, margin: '0 auto', fontFamily: mono }}>

      {/* Header */}
      <div style={{ marginBottom: 'var(--space-xl)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', letterSpacing: '0.12em', marginBottom: 4 }}>
          PROMPT FORGE
        </div>
        <div style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 600 }}>
          Опиши задачу — отримай промпт або пакет промптів
        </div>
      </div>

      {/* Provider selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-lg)' }}>
        {PROVIDERS.map(p => (
          <button
            key={p.id}
            onClick={() => setProvider(p.id)}
            style={{
              flex: 1,
              padding: '10px 8px',
              background: provider === p.id ? `${p.color}18` : 'var(--bg-elevated)',
              border: `1px solid ${provider === p.id ? p.color : 'var(--border-dim)'}`,
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'all 150ms ease',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, color: provider === p.id ? p.color : 'var(--text-secondary)', letterSpacing: '0.08em' }}>
              {p.label}
            </div>
            <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>
              {p.sublabel}
            </div>
            <div style={{
              display: 'inline-block', marginTop: 4,
              padding: '1px 5px',
              background: provider === p.id ? `${p.color}25` : 'var(--bg-tertiary)',
              borderRadius: 3,
              fontSize: 8,
              color: provider === p.id ? p.color : 'var(--text-dim)',
              letterSpacing: '0.06em',
            }}>
              {p.badge}
            </div>
          </button>
        ))}
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 'var(--space-lg)' }}>
        {(['single', 'bundle'] as ForgeMode[]).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            style={{
              padding: '5px 14px',
              background: mode === m ? 'var(--bg-quaternary)' : 'transparent',
              border: `1px solid ${mode === m ? 'var(--text-primary)' : 'var(--border-dim)'}`,
              borderRadius: 3,
              cursor: 'pointer',
              fontSize: 10,
              fontFamily: mono,
              color: mode === m ? 'var(--text-primary)' : 'var(--text-dim)',
              letterSpacing: '0.1em',
              transition: 'all 150ms ease',
            }}
          >
            {m === 'single' ? 'SINGLE PROMPT' : 'BUNDLE'}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--text-dim)', alignSelf: 'center' }}>
          {mode === 'bundle' ? 'SYSTEM + TEMPLATE + EXAMPLES + ANTI-PATTERNS' : 'ONE PRODUCTION-READY SYSTEM PROMPT'}
        </div>
      </div>

      {/* Input */}
      <div style={{ marginBottom: 'var(--space-lg)' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={`Опиши задачу, ціль, контекст.\n\nПриклад: "Мені потрібен агент для code review PR-ів на Python. Повинен перевіряти безпеку, стиль, і тести. Виводити markdown звіт."`}
          rows={6}
          style={{
            width: '100%',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-dim)',
            color: 'var(--text-primary)',
            fontFamily: mono,
            fontSize: 12,
            padding: '12px 14px',
            borderRadius: 6,
            outline: 'none',
            resize: 'vertical',
            lineHeight: 1.6,
            boxSizing: 'border-box',
          }}
          onFocus={e => { e.currentTarget.style.borderColor = activeProvider.color; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-dim)'; }}
          disabled={status === 'streaming'}
        />
      </div>

      {/* Submit / Stop */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-xl)' }}>
        <button
          onClick={status === 'streaming' ? handleStop : handleSubmit}
          disabled={status !== 'streaming' && !input.trim()}
          style={{
            padding: '10px 24px',
            background: status === 'streaming'
              ? '#ff2d5518'
              : !input.trim() ? 'var(--bg-elevated)' : `${activeProvider.color}18`,
            border: `1px solid ${status === 'streaming' ? '#ff2d55' : !input.trim() ? 'var(--border-dim)' : activeProvider.color}`,
            borderRadius: 4,
            cursor: status === 'streaming' || input.trim() ? 'pointer' : 'default',
            fontFamily: mono,
            fontSize: 11,
            fontWeight: 700,
            color: status === 'streaming' ? '#ff2d55' : !input.trim() ? 'var(--text-dim)' : activeProvider.color,
            letterSpacing: '0.1em',
            opacity: status !== 'streaming' && !input.trim() ? 0.4 : 1,
            transition: 'all 150ms ease',
          }}
        >
          {status === 'streaming' ? '■ STOP' : `▶ FORGE via ${activeProvider.label}`}
        </button>

        {status === 'streaming' && (
          <div style={{ alignSelf: 'center', fontSize: 10, color: activeProvider.color, animation: 'pulse 1s infinite' }}>
            ● streaming...
          </div>
        )}
      </div>

      {/* Output */}
      {(output || status === 'error') && (
        <div style={{ position: 'relative' }}>
          {/* Toolbar */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-dim)',
            borderBottom: 'none',
            borderRadius: '6px 6px 0 0',
          }}>
            <div style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>
              OUTPUT · {activeProvider.label} · {mode.toUpperCase()}
              {status === 'done' && <span style={{ color: '#00e87a', marginLeft: 8 }}>✓ DONE</span>}
            </div>
            {output && (
              <button
                onClick={handleCopy}
                style={{
                  padding: '3px 10px',
                  background: copied ? '#00e87a18' : 'var(--bg-tertiary)',
                  border: `1px solid ${copied ? '#00e87a' : 'var(--border-dim)'}`,
                  borderRadius: 3,
                  cursor: 'pointer',
                  fontFamily: mono,
                  fontSize: 9,
                  color: copied ? '#00e87a' : 'var(--text-secondary)',
                  letterSpacing: '0.08em',
                  transition: 'all 150ms ease',
                }}
              >
                {copied ? '✓ COPIED' : 'COPY'}
              </button>
            )}
          </div>

          {/* Content */}
          {status === 'error' ? (
            <div style={{
              padding: '12px 14px',
              background: '#ff2d5508',
              border: '1px solid #ff2d5540',
              borderRadius: '0 0 6px 6px',
              fontSize: 11,
              color: '#ff2d55',
              fontFamily: mono,
            }}>
              ✕ {errorMsg}
            </div>
          ) : (
            <pre style={{
              margin: 0,
              padding: '14px 16px',
              background: 'var(--bg-void)',
              border: '1px solid var(--border-dim)',
              borderRadius: '0 0 6px 6px',
              fontSize: 11,
              color: 'var(--text-primary)',
              fontFamily: mono,
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: 600,
              overflowY: 'auto',
            }}>
              {output}
              {status === 'streaming' && (
                <span style={{ color: activeProvider.color, animation: 'pulse 0.8s infinite' }}>▋</span>
              )}
            </pre>
          )}
        </div>
      )}

    </div>
  );
}
