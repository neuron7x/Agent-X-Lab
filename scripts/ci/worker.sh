#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

npm --prefix workers/axl-bff ci
if npm --prefix workers/axl-bff run | rg -q '^  lint$'; then
  npm --prefix workers/axl-bff run lint
else
  npx --prefix workers/axl-bff tsc --noEmit
fi

if npm --prefix workers/axl-bff run | rg -q '^  typecheck$'; then
  npm --prefix workers/axl-bff run typecheck
else
  npx --prefix workers/axl-bff tsc --noEmit
fi
