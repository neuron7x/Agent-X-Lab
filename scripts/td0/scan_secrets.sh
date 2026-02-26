#!/usr/bin/env bash

export LC_ALL=C
export LANG=C

JSON_OUT=""
if [ "${1:-}" = "--json-out" ]; then
  JSON_OUT="${2:-}"
fi

patterns=(
  "AKIA"
  "-----BEGIN"
  "xoxb-"
  "ghp_"
  "sk-"
  "OPENAI_API_KEY"
  "ANTHROPIC_API_KEY"
  "PRIVATE_KEY"
  "BEGIN RSA"
)

mapfile -t files < <(git ls-files | sort)
findings_file="$(mktemp)"
> "$findings_file"

for file in "${files[@]}"; do
  [ -f "$file" ] || continue
  for pat in "${patterns[@]}"; do
    if grep -nF "$pat" "$file" >/dev/null 2>&1; then
      while IFS= read -r line; do
        printf '%s\n' "$line" >> "$findings_file"
      done < <(grep -nF "$pat" "$file" | sed "s|^|$file:|")
    fi
  done
done

sort -u "$findings_file" -o "$findings_file"

if [ -n "$JSON_OUT" ]; then
  python3 - "$findings_file" "$JSON_OUT" <<'PY'
import json
import sys
findings_path, out_path = sys.argv[1], sys.argv[2]
items = []
with open(findings_path, 'r', encoding='utf-8') as f:
    for line in f:
        s = line.strip()
        if s:
            items.append(s)
with open(out_path, 'w', encoding='utf-8') as out:
    json.dump(items, out, indent=2)
    out.write('\n')
PY
fi

if [ -s "$findings_file" ]; then
  echo "# Secret findings"
  cat "$findings_file"
  rm -f "$findings_file"
  exit 2
fi

echo "# Secret findings"
echo "none"
rm -f "$findings_file"
exit 0
