#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

python_version=$(cat .python-version)
python_bin="python${python_version%.*}"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin="python3"
fi

"$python_bin" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r engine/requirements-dev.txt

python -m ruff check engine udgs_core tools
python -m pytest engine udgs_core
