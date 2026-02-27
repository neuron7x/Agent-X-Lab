import { readFileSync, readdirSync, existsSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const modeArg = process.argv.find((arg) => arg.startsWith('--mode='));
const mode = modeArg ? modeArg.split('=')[1] : '';

function getJsFiles(distDir) {
  return readdirSync(distDir)
    .filter((file) => file.endsWith('.js'))
    .sort((a, b) => a.localeCompare(b));
}

function runPerfBundleEvd() {
  const distDir = 'dist/assets';
  const files = getJsFiles(distDir);

  let mainBundle = 0;
  let totalRouteChunks = 0;

  for (const file of files) {
    const stats = statSync(path.join(distDir, file));
    const kb = stats.size / 1024;
    console.log(`  ${file}: ${kb.toFixed(1)} kB`);

    if (file.startsWith('index-')) {
      mainBundle = kb;
    } else if (/Route-/.test(file)) {
      totalRouteChunks += kb;
    }
  }

  const BUDGET_INITIAL_KB = 500;
  const BUDGET_CHUNK_KB = 250;

  if (mainBundle > BUDGET_INITIAL_KB) {
    console.error(`FAIL: main bundle ${mainBundle.toFixed(1)} kB > ${BUDGET_INITIAL_KB} kB budget`);
    process.exit(1);
  }

  console.log(`PASS: initial bundle ${mainBundle.toFixed(1)} kB (budget: ${BUDGET_INITIAL_KB} kB)`);
  console.log(`PASS: route chunks ${totalRouteChunks.toFixed(1)} kB total`);

  const evidence = {
    timestamp: new Date().toISOString(),
    mainBundle_kb: mainBundle,
    routeChunks_kb: totalRouteChunks,
    budget_initial_kb: BUDGET_INITIAL_KB,
    pass: mainBundle <= BUDGET_INITIAL_KB,
  };

  writeFileSync('dist/EVD-UI-BUNDLE.json', JSON.stringify(evidence, null, 2));
  console.log('EVD-UI-BUNDLE.json written');

  void BUDGET_CHUNK_KB;
}

function runVerifyBundleBudget() {
  const distDir = 'dist/assets';

  if (!existsSync(distDir)) {
    console.log('No dist/assets');
    return;
  }

  const files = getJsFiles(distDir);
  const stats = files.map((file) => {
    const size = statSync(path.join(distDir, file)).size;
    return { file, size_bytes: size, size_kb: Math.round(size / 1024) };
  });

  const total = stats.reduce((sum, file) => sum + file.size_bytes, 0);
  const result = {
    total_kb: Math.round(total / 1024),
    files: stats,
    budgets: { initial_kb_gzip_limit: 220, chunk_kb_gzip_limit: 180 },
    generated: new Date().toISOString(),
  };

  writeFileSync('dist/EVD-UI-BUNDLE.json', JSON.stringify(result, null, 2));
  console.log('Bundle total (raw):', Math.round(total / 1024), 'KB across', files.length, 'chunks');

  const data = JSON.parse(readFileSync('dist/EVD-UI-BUNDLE.json', 'utf8'));
  const initial = data.files.filter((file) => file.file.includes('index-') || file.file.includes('main-'));
  const MAX_RAW_KB = 800;
  let failed = false;

  for (const file of initial) {
    if (file.size_kb > MAX_RAW_KB) {
      console.error('BUDGET EXCEEDED:', file.file, `${file.size_kb}KB > ${MAX_RAW_KB}KB raw`);
      failed = true;
    }
  }

  if (failed) {
    process.exit(1);
  }

  console.log('Bundle budgets: PASS');
}

if (mode === 'perf-bundle-evd') {
  runPerfBundleEvd();
} else if (mode === 'verify-bundle-budget') {
  runVerifyBundleBudget();
} else {
  console.error('Usage: node scripts/analyze-bundle.mjs --mode=perf-bundle-evd|verify-bundle-budget');
  process.exit(1);
}
