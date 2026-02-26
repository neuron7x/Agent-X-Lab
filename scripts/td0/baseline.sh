#!/usr/bin/env bash

export PYTHONHASHSEED=0
export LC_ALL=C
export LANG=C
export TZ=UTC
export GIT_PAGER=cat
export PAGER=cat
export PYTHONDONTWRITEBYTECODE=1

mkdir -p evidence
LOG_FILE="evidence/TD0_COMMAND_LOG.txt"
CHECKS_FILE="$(mktemp)"
BLOCKED_FILE="$(mktemp)"
LARGE_FILE_JSON="evidence/.td0_large_files.json"
SECRETS_JSON="evidence/.td0_secrets_findings.json"

: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

run() { echo "+ $*"; "$@"; rc=$?; echo "EXIT_CODE=$rc"; return $rc; }
record_check() {
  name="$1"
  cmd="$2"
  rc="$3"
  printf '%s\t%s\t%s\n' "$name" "$cmd" "$rc" >> "$CHECKS_FILE"
}
record_blocked() {
  name="$1"
  reason="$2"
  printf '%s\t%s\n' "$name" "$reason" >> "$BLOCKED_FILE"
}

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
commit="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then dirty=true; else dirty=false; fi

echo "# TD0 baseline started"

run git status --porcelain
record_check "git_status" "git status --porcelain" "$?"

if command -v node >/dev/null 2>&1; then
  node_ver="$(node -v 2>/dev/null || echo missing)"
  run node -v
  record_check "node_version" "node -v" "$?"
else
  node_ver="missing"
  echo "+ node -v"
  echo "EXIT_CODE=127"
  record_check "node_version" "node -v" "127"
fi

if command -v npm >/dev/null 2>&1; then
  npm_ver="$(npm -v 2>/dev/null || echo missing)"
  run npm -v
  record_check "npm_version" "npm -v" "$?"
else
  npm_ver="missing"
  echo "+ npm -v"
  echo "EXIT_CODE=127"
  record_check "npm_version" "npm -v" "127"
fi

py_ver="$(python3 --version 2>/dev/null || echo missing)"
run python3 --version
record_check "python_version" "python3 --version" "$?"

if [ -f package-lock.json ]; then
  record_blocked "npm_install" "offline_only"
  echo "+ npm ci"
  echo "SKIPPED=offline_only"
else
  record_blocked "npm_install" "offline_only"
  echo "+ npm install --no-audit --no-fund"
  echo "SKIPPED=offline_only"
fi

run npm run lint
record_check "lint" "npm run lint" "$?"
run npm run typecheck
record_check "typecheck" "npm run typecheck" "$?"
run npm run test:unit -- --coverage
record_check "test_unit_coverage" "npm run test:unit -- --coverage" "$?"
run npm run build
record_check "build" "npm run build" "$?"

if [ -d workers/axl-bff ]; then
  record_blocked "worker_npm_install" "offline_only"
  echo "+ cd workers/axl-bff && npm ci"
  echo "SKIPPED=offline_only"
  run bash -lc 'cd workers/axl-bff && npm run typecheck'
  record_check "worker_typecheck" "cd workers/axl-bff && npm run typecheck" "$?"
fi

run python3 scripts/td0/scan_large_files.py --json-out "$LARGE_FILE_JSON"
record_check "scan_large_files" "python3 scripts/td0/scan_large_files.py" "$?"

run bash scripts/td0/scan_secrets.sh --json-out "$SECRETS_JSON"
record_check "scan_secrets" "bash scripts/td0/scan_secrets.sh" "$?"

python3 - "$branch" "$commit" "$dirty" "$node_ver" "$npm_ver" "$py_ver" "$CHECKS_FILE" "$BLOCKED_FILE" "$LARGE_FILE_JSON" "$SECRETS_JSON" <<'PY'
import json
import sys
from datetime import datetime, timezone

(
    branch,
    commit,
    dirty,
    node_ver,
    npm_ver,
    py_ver,
    checks_file,
    blocked_file,
    large_file_json,
    secrets_json,
) = sys.argv[1:]

checks = []
with open(checks_file, 'r', encoding='utf-8') as f:
    for line in f:
        s = line.rstrip('\n')
        if not s:
            continue
        name, cmd, rc = s.split('\t')
        checks.append({"name": name, "cmd": cmd, "exit": int(rc)})

blocked = []
with open(blocked_file, 'r', encoding='utf-8') as f:
    for line in f:
        s = line.rstrip('\n')
        if not s:
            continue
        name, reason = s.split('\t', 1)
        blocked.append({"name": name, "reason": reason})

large_files = []
try:
    with open(large_file_json, 'r', encoding='utf-8') as f:
        large_files = json.load(f)
except FileNotFoundError:
    large_files = []

secrets_findings = []
try:
    with open(secrets_json, 'r', encoding='utf-8') as f:
        secrets_findings = json.load(f)
except FileNotFoundError:
    secrets_findings = []

baseline = {
    "git": {"branch": branch, "commit": commit, "dirty": dirty == "true"},
    "env": {"node": node_ver, "npm": npm_ver, "python": py_ver},
    "checks": checks,
    "blocked": blocked,
    "large_files": large_files,
    "secrets_findings": secrets_findings,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}

with open('evidence/TD0_BASELINE.json', 'w', encoding='utf-8') as out:
    json.dump(baseline, out, indent=2, sort_keys=True)
    out.write('\n')
PY

rm -f "$CHECKS_FILE" "$BLOCKED_FILE" "$LARGE_FILE_JSON" "$SECRETS_JSON"
echo "# TD0 baseline completed"
exit 0
