#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

npm ci

if npm --prefix workers/axl-bff run | rg -q '^  lint$'; then
  npm --prefix workers/axl-bff run lint
fi

if npm --prefix workers/axl-bff run | rg -q '^  typecheck$'; then
  npm --prefix workers/axl-bff run typecheck
else
  npx tsc -p workers/axl-bff/tsconfig.json --noEmit
fi
