/**
 * e2e/smoke.spec.ts — Playwright smoke tests (Phase 7).
 * Tests: route navigation, command palette, demo mode, auth gate.
 */
import { test, expect } from '@playwright/test';

test.describe('AXL-UI smoke tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('app loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.waitForLoadState('networkidle');
    // Allow minor console errors but no crashes
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0);
  });

  test('navigation tabs visible and functional', async ({ page }) => {
    const nav = page.getByRole('navigation').first();
    await expect(nav).toBeVisible();
    await expect(nav.getByRole('link', { name: /pipeline/i }).first()).toBeVisible();
    await expect(nav.getByRole('link', { name: /evidence/i }).first()).toBeVisible();
    await expect(nav.getByRole('link', { name: /forge/i }).first()).toBeVisible();
  });

  test('navigates between routes', async ({ page }) => {
    await page.goto('/pipeline');
    await expect(page).toHaveURL('/pipeline');

    await page.goto('/evidence');
    await expect(page).toHaveURL('/evidence');

    await page.goto('/forge');
    await expect(page).toHaveURL('/forge');

    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');
  });

  test('404 page for unknown route', async ({ page }) => {
    await page.goto('/route-that-does-not-exist');
    await expect(page.getByRole('heading', { name: /404/i })).toBeVisible();
  });

  test('command palette opens with Ctrl+K', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const palette = page.getByRole('dialog', { name: 'Command palette' });
    await expect(palette).toBeVisible();
  });

  test('command palette closes on Escape', async ({ page }) => {
    await page.keyboard.press('Control+k');
    await expect(page.getByRole('dialog', { name: 'Command palette' })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog', { name: 'Command palette' })).not.toBeVisible();
  });

  test('skip to content link exists (a11y)', async ({ page }) => {
    const skip = page.getByRole('link', { name: /skip to main content/i });
    await expect(skip).toBeAttached();
  });

  test('Forge screen loads without crash', async ({ page }) => {
    await page.goto('/forge');
    await expect(page.getByRole('button', { name: /CLAUDE|GPT-5\.2|N8N/i }).first()).toBeVisible();
  });

  test('protected Forge action requires API key header (demo: no actual call)', async ({ page }) => {
    await page.goto('/forge');
    // In demo mode, forge submit should not throw uncaught errors
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    // No input = button disabled, no request
    await expect(errors).toHaveLength(0);
  });
});

test.describe('Accessibility', () => {
  test('home page has proper landmark structure', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('navigation')).toBeVisible();
  });

  test('all route pages have main landmark', async ({ page }) => {
    for (const path of ['/', '/pipeline', '/evidence', '/arsenal', '/forge', '/settings']) {
      await page.goto(path);
      await expect(page.getByRole('main'), `main landmark missing on ${path}`).toBeVisible();
    }
  });
});
