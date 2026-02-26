#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

npm ci
npx playwright install --with-deps chromium
VITE_AXL_API_BASE='http://localhost:4173' VITE_AXL_API_KEY='e2e-test-key' npm run build
npm run test:e2e -- --grep @smoke
