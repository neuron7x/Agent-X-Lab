import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const outputPath = path.resolve('dist', 'EVD-UI-A11Y.json');
mkdirSync(path.dirname(outputPath), { recursive: true });

const result = spawnSync(
  process.execPath,
  [
    'node_modules/vitest/vitest.mjs',
    'run',
    'src/test/a11y.test.tsx',
    '--reporter=verbose',
    '--reporter=json',
    '--outputFile',
    outputPath,
  ],
  { stdio: 'inherit' },
);

if (!existsSync(outputPath)) {
  const placeholder = {
    status: 'failed-to-produce-report',
    exit_code: result.status ?? 1,
    signal: result.signal ?? null,
  };
  writeFileSync(outputPath, `${JSON.stringify(placeholder, null, 2)}\n`);
}

if (typeof result.status === 'number') {
  process.exit(result.status);
}

process.exit(1);
