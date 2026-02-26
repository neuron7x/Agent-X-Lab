#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C
export TZ=UTC

baseline_file="evidence/ui_bundle_baseline.json"
report_file="evidence/ui_bundle_size.txt"

if [ ! -f "$baseline_file" ]; then
  echo "Missing baseline file: $baseline_file" >&2
  exit 1
fi

mapfile -t asset_files < <(find dist/assets -maxdepth 1 -type f \( -name '*.js' -o -name '*.css' \) | sort)

if [ "${#asset_files[@]}" -eq 0 ]; then
  echo "No dist/assets JS/CSS files found. Did you run build?" >&2
  exit 1
fi

total_js=0
total_css=0
for file in "${asset_files[@]}"; do
  size=$(wc -c < "$file")
  case "$file" in
    *.js) total_js=$((total_js + size)) ;;
    *.css) total_css=$((total_css + size)) ;;
  esac
done

total=$((total_js + total_css))
baseline_total=$(python3 - <<'PY'
import json
with open('evidence/ui_bundle_baseline.json', 'r', encoding='utf-8') as f:
    print(json.load(f)['total'])
PY
)
delta=$((total - baseline_total))

mkdir -p evidence
{
  echo "baseline_total=$baseline_total"
  echo "current_total=$total"
  echo "delta=$delta"
  echo "total_js=$total_js"
  echo "total_css=$total_css"
  echo "files:"
  for file in "${asset_files[@]}"; do
    printf '%s %s\n' "$(wc -c < "$file")" "$file"
  done
} > "$report_file"

if [ "$delta" -gt 5120 ]; then
  echo "Bundle size regression exceeds +5KB: delta=$delta bytes" >&2
  exit 1
fi
