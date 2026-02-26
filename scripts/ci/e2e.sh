#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

npm ci
npx playwright install --with-deps chromium
npm run test:e2e -- --grep @smoke
