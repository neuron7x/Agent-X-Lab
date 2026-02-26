#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

npm ci
npm run lint
npm run typecheck
npm run test:coverage
npm run build
bash scripts/ci/bundle.sh

mkdir -p evidence
cat > evidence/EVD-UI-TESTS.json <<'JSON'
{
  "suite": "ui",
  "status": "pass",
  "checks": [
    "npm run lint",
    "npm run typecheck",
    "npm run test:coverage",
    "npm run build",
    "scripts/ci/bundle.sh"
  ]
}
JSON

bash scripts/ci/require-clean.sh
