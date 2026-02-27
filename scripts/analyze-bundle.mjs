import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { gzipSync } from 'node:zlib';

export const BUDGETS = {
  entry_gzip_kb: 220,
  chunk_gzip_kb: 180,
};

function toKb(bytes) {
  return Number((bytes / 1024).toFixed(2));
}

function classifyFiles(files, distRoot) {
  const manifestPath = path.join(distRoot, '.vite', 'manifest.json');
  const fallbackEntry = files.filter((file) => file.startsWith('index-') || file.startsWith('main-')).sort((a, b) => a.localeCompare(b));

  if (!existsSync(manifestPath)) {
    const entrySet = new Set(fallbackEntry);
    return {
      source: 'fallback',
      entryFiles: fallbackEntry,
      nonEntryFiles: files.filter((file) => !entrySet.has(file)).sort((a, b) => a.localeCompare(b)),
    };
  }

  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const entryFiles = Object.values(manifest)
    .filter((item) => item && item.isEntry === true && typeof item.file === 'string' && item.file.endsWith('.js'))
    .map((item) => path.basename(item.file))
    .filter((file) => files.includes(file))
    .sort((a, b) => a.localeCompare(b));

  if (entryFiles.length === 0) {
    const entrySet = new Set(fallbackEntry);
    return {
      source: 'fallback-no-entry-in-manifest',
      entryFiles: fallbackEntry,
      nonEntryFiles: files.filter((file) => !entrySet.has(file)).sort((a, b) => a.localeCompare(b)),
    };
  }

  const entrySet = new Set(entryFiles);
  return {
    source: 'manifest',
    entryFiles,
    nonEntryFiles: files.filter((file) => !entrySet.has(file)).sort((a, b) => a.localeCompare(b)),
  };
}

export function analyzeBundle({ mode, distRoot = 'dist' }) {
  const assetsDir = path.join(distRoot, 'assets');
  if (!existsSync(assetsDir)) {
    throw new Error(`Missing required ${assetsDir}`);
  }

  const files = readdirSync(assetsDir)
    .filter((file) => file.endsWith('.js'))
    .sort((a, b) => a.localeCompare(b));

  const perFile = files.map((file) => {
    const filePath = path.join(assetsDir, file);
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

  const classification = classifyFiles(files, distRoot);
  const entrySet = new Set(classification.entryFiles);
  const violations = [];

  for (const item of perFile) {
    if (entrySet.has(item.file) && item.gzip_kb > BUDGETS.entry_gzip_kb) {
      violations.push(`${item.file}: ${item.gzip_kb}kB gzip > ${BUDGETS.entry_gzip_kb}kB entry budget`);
    }
    if (!entrySet.has(item.file) && item.gzip_kb > BUDGETS.chunk_gzip_kb) {
      violations.push(`${item.file}: ${item.gzip_kb}kB gzip > ${BUDGETS.chunk_gzip_kb}kB chunk budget`);
    }
  }

  const entryTotalGzipKb = toKb(perFile.filter((item) => entrySet.has(item.file)).reduce((sum, item) => sum + item.gzip_bytes, 0));
  if (entryTotalGzipKb > BUDGETS.entry_gzip_kb) {
    violations.push(`entry_total: ${entryTotalGzipKb}kB gzip > ${BUDGETS.entry_gzip_kb}kB entry budget`);
  }

  return {
    mode,
    generated_utc: new Date().toISOString(),
    dist_assets: assetsDir,
    classification_source: classification.source,
    budgets: BUDGETS,
    files: perFile,
    entry_files: classification.entryFiles,
    non_entry_files: classification.nonEntryFiles,
    violations,
    pass: violations.length === 0,
  };
}

export function writeBundleEvidence(evidence, { distRoot = 'dist' } = {}) {
  const outPath = path.join(distRoot, 'EVD-UI-BUNDLE.json');
  mkdirSync(distRoot, { recursive: true });
  writeFileSync(outPath, `${JSON.stringify(evidence, null, 2)}\n`);
  return outPath;
}

function runCli() {
  const modeArg = process.argv.find((arg) => arg.startsWith('--mode='));
  const mode = modeArg ? modeArg.split('=')[1] : '';
  if (mode !== 'perf-bundle-evd' && mode !== 'verify-bundle-budget') {
    console.error('Usage: node scripts/analyze-bundle.mjs --mode=perf-bundle-evd|verify-bundle-budget');
    process.exit(1);
  }

  const evidence = analyzeBundle({ mode });
  for (const item of evidence.files) {
    console.log(`  ${item.file}: raw ${item.raw_kb} kB | gzip ${item.gzip_kb} kB`);
  }

  const outPath = writeBundleEvidence(evidence);
  console.log(`Wrote ${outPath}`);

  if (!evidence.pass) {
    for (const violation of evidence.violations) {
      console.error(`BUDGET EXCEEDED: ${violation}`);
    }
    process.exit(1);
  }

  console.log('Bundle budgets: PASS');
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  runCli();
}
