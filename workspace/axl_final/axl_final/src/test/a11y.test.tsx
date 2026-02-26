/**
 * src/test/a11y.test.tsx
 * GATE-4 evidence: axe accessibility checks on key components.
 * D5: a11y test pyramid layer.
 * I5: WCAG 2.2 AA baseline enforcement.
 * Uses axe-core directly (no jest-axe needed).
 */
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LanguageProvider } from '@/hooks/useLanguage';
import axe from 'axe-core';
import { ForgeScreen } from '@/components/axl/ForgeScreen';
import { SkeletonPanel } from '@/components/axl/SkeletonPanel';
import { CommandPalette } from '@/components/shell/CommandPalette';

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function Wrap({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LanguageProvider>{children}</LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

async function runAxe(container: HTMLElement, disableRules: string[] = []) {
  const config: axe.RunOptions = {
    rules: Object.fromEntries(disableRules.map(r => [r, { enabled: false }])),
  };
  const results = await axe.run(container, config);
  return results.violations;
}

// Disable color-contrast in all a11y tests — runtime CSS vars not resolved in jsdom
const SKIP_RULES = ['color-contrast'];

describe('Accessibility (axe-core WCAG 2.2 AA)', () => {
  it('SkeletonPanel has no critical axe violations', async () => {
    const { container } = render(<SkeletonPanel />);
    const violations = await runAxe(container, SKIP_RULES);
    const critical = violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(
      critical.map(v => `${v.id}: ${v.description}`),
      'Critical a11y violations found'
    ).toHaveLength(0);
  });

  it('ForgeScreen has no critical axe violations', async () => {
    const { container } = render(<Wrap><ForgeScreen /></Wrap>);
    const violations = await runAxe(container, SKIP_RULES);
    const critical = violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(
      critical.map(v => `${v.id}: ${v.description}`),
    ).toHaveLength(0);
  });

  it('CommandPalette has no critical axe violations', async () => {
    const { container } = render(<Wrap><CommandPalette onClose={() => {}} /></Wrap>);
    const violations = await runAxe(container, SKIP_RULES);
    const critical = violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(
      critical.map(v => `${v.id}: ${v.description}`),
    ).toHaveLength(0);
  });
});

describe('WCAG structure invariants', () => {
  it('ForgeScreen buttons have accessible names', () => {
    const { getAllByRole } = render(<Wrap><ForgeScreen /></Wrap>);
    const buttons = getAllByRole('button');
    for (const btn of buttons) {
      const name = btn.textContent?.trim() || btn.getAttribute('aria-label');
      expect(name, `Button missing accessible name: ${btn.outerHTML.slice(0, 80)}`).toBeTruthy();
    }
  });

  it('ForgeScreen has textbox for user input', () => {
    const { getByRole } = render(<Wrap><ForgeScreen /></Wrap>);
    expect(getByRole('textbox')).toBeInTheDocument();
  });

  it('CommandPalette has dialog role', () => {
    const { getByRole } = render(<Wrap><CommandPalette onClose={() => {}} /></Wrap>);
    expect(getByRole('dialog')).toBeInTheDocument();
  });

  it('CommandPalette dialog has aria-label', () => {
    const { getByRole } = render(<Wrap><CommandPalette onClose={() => {}} /></Wrap>);
    expect(getByRole('dialog')).toHaveAttribute('aria-label', 'Command palette');
  });
});
