import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

const modeArg = process.argv.find((arg) => arg.startsWith('--mode='));
const mode = modeArg ? modeArg.split('=')[1] : '';
const distDir = 'dist/assets';
const outputPath = 'dist/EVD-UI-BUNDLE.json';

const BUDGET_INITIAL_GZIP_KB = 220;
const BUDGET_CHUNK_GZIP_KB = 180;

function toKb(bytes) {
  return Number((bytes / 1024).toFixed(2));
}

function readJsFileStats() {
  if (!existsSync(distDir)) {
    throw new Error(`Missing required ${distDir}`);
  }

  return readdirSync(distDir)
    .filter((file) => file.endsWith('.js'))
    .sort((a, b) => a.localeCompare(b))
    .map((file) => {
      const filePath = path.join(distDir, file);
      const rawBytes = statSync(filePath).size;
      const gzipBytes = gzipSync(readFileSync(filePath)).length;
      return {
        file,
        raw_bytes: rawBytes,
        gzip_bytes: gzipBytes,
        raw_kb: toKb(rawBytes),
        gzip_kb: toKb(gzipBytes),
      };
    });
}

function summarize(files) {
  const initialFiles = files.filter((file) => file.file.startsWith('index-') || file.file.startsWith('main-'));
  const routeFiles = files.filter((file) => /Route-/.test(file.file));
  const violations = [];

  for (const file of initialFiles) {
    if (file.gzip_kb > BUDGET_INITIAL_GZIP_KB) {
      violations.push(`${file.file}: ${file.gzip_kb}kB gzip > ${BUDGET_INITIAL_GZIP_KB}kB`);
    }
  }

  for (const file of routeFiles) {
    if (file.gzip_kb > BUDGET_CHUNK_GZIP_KB) {
      violations.push(`${file.file}: ${file.gzip_kb}kB gzip > ${BUDGET_CHUNK_GZIP_KB}kB`);
    }
  }

  return {
    initial_files: initialFiles.map((file) => file.file),
    route_files: routeFiles.map((file) => file.file),
    initial_total_raw_kb: toKb(initialFiles.reduce((sum, file) => sum + file.raw_bytes, 0)),
    initial_total_gzip_kb: toKb(initialFiles.reduce((sum, file) => sum + file.gzip_bytes, 0)),
    route_total_raw_kb: toKb(routeFiles.reduce((sum, file) => sum + file.raw_bytes, 0)),
    route_total_gzip_kb: toKb(routeFiles.reduce((sum, file) => sum + file.gzip_bytes, 0)),
    total_raw_kb: toKb(files.reduce((sum, file) => sum + file.raw_bytes, 0)),
    total_gzip_kb: toKb(files.reduce((sum, file) => sum + file.gzip_bytes, 0)),
    budget_initial_gzip_kb: BUDGET_INITIAL_GZIP_KB,
    budget_chunk_gzip_kb: BUDGET_CHUNK_GZIP_KB,
    pass: violations.length === 0,
    violations,
  };
}

function writeEvidence(modeName, files, summary) {
  const evidence = {
    mode: modeName,
    generated_utc: new Date().toISOString(),
    dist_assets: distDir,
    files,
    summary,
  };

  writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`);
  console.log(`Wrote ${outputPath}`);
}

function run(modeName) {
  const files = readJsFileStats();
  const summary = summarize(files);

  for (const file of files) {
    console.log(`  ${file.file}: raw ${file.raw_kb} kB | gzip ${file.gzip_kb} kB`);
  }
  console.log(`Summary: raw ${summary.total_raw_kb} kB | gzip ${summary.total_gzip_kb} kB`);

  writeEvidence(modeName, files, summary);

  if (!summary.pass) {
    for (const violation of summary.violations) {
      console.error(`BUDGET EXCEEDED: ${violation}`);
    }
    process.exit(1);
  }

  console.log('Bundle budgets: PASS');
}

if (mode === 'perf-bundle-evd' || mode === 'verify-bundle-budget') {
  run(mode);
} else {
  console.error('Usage: node scripts/analyze-bundle.mjs --mode=perf-bundle-evd|verify-bundle-budget');
  process.exit(1);
}
