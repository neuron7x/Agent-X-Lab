#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo ".env must not be tracked" >&2
  exit 1
fi

if [ -f .env ] && [ ! -f .env.example ]; then
  echo ".env.example is required when .env exists" >&2
  exit 1
fi

if ! git diff --quiet -- .; then
  echo "Tracked files changed during CI run. Commit generated artifacts or fix scripts." >&2
  git status --short
  exit 1
fi
