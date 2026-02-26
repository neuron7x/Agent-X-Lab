import type { PullRequest } from '@/lib/types';

interface PRTrackerProps {
  prs: PullRequest[];
}

export function PRTracker({ prs }: PRTrackerProps) {
  return (
    <div className="axl-panel p-4 mt-3" style={{ animation: 'stagger-reveal 0.3s ease-out forwards', animationDelay: '240ms' }}>
      <h2 className="axl-label mb-3" style={{ fontSize: '12px' }}>ACTIVE PRs</h2>

      {prs.length === 0 ? (
        <div className="flex items-center justify-center h-12">
          <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-dim)' }}>NO PRs</span>
        </div>
      ) : (
        <div className="flex flex-col gap-0">
          {prs.map((pr) => {
            const allPassed = pr.checksPassed === pr.checksTotal && pr.checksTotal > 0;
            return (
              <a
                key={pr.number}
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 py-2 px-1 cursor-pointer"
                style={{
                  borderBottom: '1px solid var(--border-dim)',
                  textDecoration: 'none',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <span className="font-mono font-medium" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  #{pr.number}
                </span>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '10px',
                    color: allPassed ? '#00e87a' : '#ffaa00',
                    background: allPassed ? '#00e87a15' : '#ffaa0015',
                    border: `1px solid ${allPassed ? '#00e87a40' : '#ffaa0040'}`,
                    padding: '0 5px',
                    borderRadius: '2px',
                  }}
                  aria-label={`${pr.checksPassed} of ${pr.checksTotal} checks passed`}
                >
                  ● {pr.checksPassed}/{pr.checksTotal}
                </span>
                <span
                  className="font-mono truncate"
                  style={{ fontSize: '11px', color: 'var(--text-primary)' }}
                >
                  {pr.title}
                </span>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
