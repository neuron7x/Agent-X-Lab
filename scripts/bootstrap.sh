#!/usr/bin/env bash
set -euo pipefail

NODE_PIN="$(cat .node-version)"
PY_PIN="$(cat .python-version)"
NODE_CUR="$(node -v | sed 's/^v//')"
PY_CUR="$(python3 -c 'import platform; print(platform.python_version())')"

if [ "$NODE_CUR" != "$NODE_PIN" ]; then
  echo "ERROR: node version mismatch. expected=${NODE_PIN} current=${NODE_CUR}" >&2
  exit 1
fi
if [ "$PY_CUR" != "$PY_PIN" ]; then
  echo "ERROR: python version mismatch. expected=${PY_PIN} current=${PY_CUR}" >&2
  exit 1
fi

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
if [ -f engine/pyproject.toml ]; then
  pip install -e engine
fi
if [ -f package-lock.json ]; then
  npm ci
fi

echo "Bootstrap complete. Activate venv with: source .venv/bin/activate"
echo "Next: make dev-ui | make dev-worker | make test"
