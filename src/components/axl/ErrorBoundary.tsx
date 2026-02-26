import { Component, type ReactNode, type ErrorInfo } from 'react';
import { translations } from '@/lib/i18n';
import type { Lang } from '@/lib/i18n';

interface Props {
  children: ReactNode;
  panelName?: string;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

function getLang(): Lang {
  const stored = localStorage.getItem('axl_lang');
  return (stored === 'en' || stored === 'ua') ? stored : 'ua';
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[ErrorBoundary:${this.props.panelName || 'unknown'}]`, error, info.componentStack);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      const lang = getLang();
      return (
        <div
          className="axl-panel p-6 flex flex-col items-center justify-center gap-4"
          style={{ minHeight: 120 }}
        >
          <span style={{ fontSize: 16, color: 'var(--signal-fail)', fontWeight: 600 }}>
            {translations.error[lang]}
          </span>
          <span className="text-center" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, maxWidth: 300 }}>
            {this.props.panelName ? `[${this.props.panelName}] ` : ''}
            {this.state.errorMessage}
          </span>
          <button
            onClick={this.handleReload}
            className="axl-surface"
            style={{ fontSize: 12, padding: '8px 20px', borderRadius: 999, fontWeight: 400, cursor: 'pointer' }}
          >
            {translations.reload[lang]}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
