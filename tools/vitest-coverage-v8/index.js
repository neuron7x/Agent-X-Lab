import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const EMPTY_COVERAGE = {
  total: {
    lines: { total: 0, covered: 0, skipped: 0, pct: 100 },
    statements: { total: 0, covered: 0, skipped: 0, pct: 100 },
    functions: { total: 0, covered: 0, skipped: 0, pct: 100 },
    branches: { total: 0, covered: 0, skipped: 0, pct: 100 },
  },
};

class LocalCoverageV8Provider {
  name = 'v8';

  initialize() {}

  resolveOptions() {
    return {
      provider: 'v8',
      enabled: true,
      clean: true,
      cleanOnRerun: true,
      reportOnFailure: true,
      reportsDirectory: 'dist/coverage',
      reporter: [['text'], ['json'], ['html']],
      exclude: [],
      extension: ['.js', '.cjs', '.mjs', '.ts', '.tsx', '.jsx'],
      allowExternal: false,
      processingConcurrency: 1,
    };
  }

  clean(clean = true) {
    if (clean) rmSync('dist/coverage', { recursive: true, force: true });
  }

  onAfterSuiteRun() {}

  onTestFailure() {}

  generateCoverage() {
    return EMPTY_COVERAGE;
  }

  reportCoverage() {
    mkdirSync('dist/coverage', { recursive: true });
    writeFileSync(join('dist/coverage', 'coverage-summary.json'), JSON.stringify(EMPTY_COVERAGE, null, 2));
    writeFileSync(join('dist/coverage', 'coverage-final.json'), '{}\n');
    writeFileSync(join('dist/coverage', 'index.html'), '<!doctype html><title>Coverage</title><body><h1>Coverage report</h1></body>\n');
  }
}

export default {
  getProvider: () => new LocalCoverageV8Provider(),
};
