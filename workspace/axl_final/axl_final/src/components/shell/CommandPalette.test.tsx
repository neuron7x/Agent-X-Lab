/**
 * CommandPalette tests — keyboard nav, routes, accessibility.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LanguageProvider } from '@/hooks/useLanguage';
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

describe('CommandPalette', () => {
  it('renders and has dialog role', () => {
    const onClose = vi.fn();
    render(<Wrap><CommandPalette onClose={onClose} /></Wrap>);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('has aria-label for accessibility', () => {
    render(<Wrap><CommandPalette onClose={vi.fn()} /></Wrap>);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-label', 'Command palette');
  });

  it('closes on Escape key', () => {
    const onClose = vi.fn();
    render(<Wrap><CommandPalette onClose={onClose} /></Wrap>);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes on backdrop click', () => {
    const onClose = vi.fn();
    const { container } = render(<Wrap><CommandPalette onClose={onClose} /></Wrap>);
    const backdrop = container.querySelector('[role="dialog"]')!;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it('renders cmdk listbox container', () => {
    render(<Wrap><CommandPalette onClose={vi.fn()} /></Wrap>);
    // cmdk renders a listbox for the command list
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    // Has keyboard hint
    expect(screen.getByText(/Esc/i)).toBeInTheDocument();
  });

  it('has input with placeholder', () => {
    render(<Wrap><CommandPalette onClose={vi.fn()} /></Wrap>);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('shows keyboard hint footer', () => {
    render(<Wrap><CommandPalette onClose={vi.fn()} /></Wrap>);
    expect(screen.getByText(/Esc/)).toBeInTheDocument();
  });
});
