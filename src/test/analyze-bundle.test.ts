import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { analyzeBundle, writeBundleEvidence } from '../../scripts/analyze-bundle.mjs';

function makeTempDist() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'axl-bundle-test-'));
  const distRoot = path.join(root, 'dist');
  mkdirSync(path.join(distRoot, 'assets'), { recursive: true });
  mkdirSync(path.join(distRoot, '.vite'), { recursive: true });
  return { root, distRoot };
}

function deterministicNoise(length: number) {
  let value = 123456789;
  const alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let out = '';
  for (let i = 0; i < length; i += 1) {
    value = (value * 1664525 + 1013904223) % 4294967296;
    out += alphabet[value % alphabet.length];
  }
  return out;
}

describe('analyzeBundle', () => {
  it('classifies entry and non-entry files from manifest and writes evidence', () => {
    const { root, distRoot } = makeTempDist();

    try {
      writeFileSync(path.join(distRoot, 'assets', 'entry.js'), 'console.log("entry");');
      writeFileSync(path.join(distRoot, 'assets', 'chunk-a.js'), 'console.log("chunk-a");');
      writeFileSync(path.join(distRoot, 'assets', 'chunk-b.js'), 'console.log("chunk-b");');
      writeFileSync(
        path.join(distRoot, '.vite', 'manifest.json'),
        JSON.stringify(
          {
            'src/main.tsx': { file: 'assets/entry.js', isEntry: true },
            'src/chunk-a.ts': { file: 'assets/chunk-a.js' },
            'src/chunk-b.ts': { file: 'assets/chunk-b.js' },
          },
          null,
          2,
        ),
      );

      const evidence = analyzeBundle({ mode: 'verify-bundle-budget', distRoot });
      const outPath = writeBundleEvidence(evidence, { distRoot });

      expect(evidence.entry_files).toEqual(['entry.js']);
      expect(evidence.non_entry_files).toEqual(['chunk-a.js', 'chunk-b.js']);
      expect(evidence.files.every((item) => typeof item.raw_kb === 'number' && typeof item.gzip_kb === 'number')).toBe(true);
      expect(evidence.pass).toBe(true);
      expect(path.basename(outPath)).toBe('EVD-UI-BUNDLE.json');
    } finally {
      rmSync(root, { force: true, recursive: true });
    }
  });

  it('flags violations when chunk exceeds budget', () => {
    const { root, distRoot } = makeTempDist();

    try {
      writeFileSync(path.join(distRoot, 'assets', 'entry.js'), 'console.log("entry");');
      writeFileSync(path.join(distRoot, 'assets', 'huge-chunk.js'), deterministicNoise(450_000));
      writeFileSync(
        path.join(distRoot, '.vite', 'manifest.json'),
        JSON.stringify({
          'src/main.tsx': { file: 'assets/entry.js', isEntry: true },
          'src/huge.ts': { file: 'assets/huge-chunk.js' },
        }),
      );

      const evidence = analyzeBundle({ mode: 'perf-bundle-evd', distRoot });

      expect(evidence.pass).toBe(false);
      expect(evidence.violations.length).toBeGreaterThan(0);
      expect(evidence.violations.some((msg) => msg.includes('huge-chunk.js'))).toBe(true);
    } finally {
      rmSync(root, { force: true, recursive: true });
    }
  });
});
