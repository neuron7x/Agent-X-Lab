#!/usr/bin/env bash

export LC_ALL=C
export LANG=C

JSON_OUT=""
if [ "${1:-}" = "--json-out" ]; then
  JSON_OUT="${2:-}"
fi

TEXT_EXTENSIONS=(".md" ".txt" ".yml" ".yaml" ".json" ".toml" ".ts" ".tsx" ".js" ".py" ".sh" ".env.example")
BINARY_SKIP_EXTENSIONS=(".zip" ".package" ".tgz" ".gz" ".png" ".jpg" ".jpeg" ".pdf" ".ico" ".woff" ".woff2" ".mp4" ".bin")
MAX_SIZE_BYTES=$((1024 * 1024))

should_skip_path() {
  local path="$1"
  [[ "$path" == archive/* ]] && return 0
  [[ "$path" == evidence/* ]] && return 0
  [[ "$path" == engine/tests/* ]] && return 0
  [[ "$path" == scripts/td0/scan_secrets.sh ]] && return 0
  return 1
}

is_text_candidate() {
  local path_lc="$1"
  for ext in "${TEXT_EXTENSIONS[@]}"; do
    [[ "$path_lc" == *"$ext" ]] && return 0
  done
  return 1
}

is_binary_skip_ext() {
  local path_lc="$1"
  for ext in "${BINARY_SKIP_EXTENSIONS[@]}"; do
    [[ "$path_lc" == *"$ext" ]] && return 0
  done
  return 1
}

findings_file="$(mktemp)"
> "$findings_file"

while IFS= read -r -d '' file; do
  [ -f "$file" ] || continue
  should_skip_path "$file" && continue
  file_lc="$(printf '%s' "$file" | tr '[:upper:]' '[:lower:]')"

  is_binary_skip_ext "$file_lc" && continue

  size_bytes=$(wc -c < "$file" 2>/dev/null || echo 0)
  [ "$size_bytes" -gt "$MAX_SIZE_BYTES" ] && continue

  is_text_candidate "$file_lc" || continue

  while IFS= read -r line; do
    printf '%s:%s\n' "$file" "$line" >> "$findings_file"
  done < <(
    grep -nIE \
      -e 'ghp_[A-Za-z0-9]{36,}' \
      -e 'sk-[A-Za-z0-9-]{20,}' \
      -e 'AKIA[0-9A-Z]{16}' \
      -e 'xoxb-[A-Za-z0-9-]{10,}' \
      -e '-----BEGIN( [A-Z]+)? PRIVATE KEY-----' \
      -e 'BEGIN RSA PRIVATE KEY' \
      -e "(OPENAI_API_KEY|ANTHROPIC_API_KEY|PRIVATE_KEY)[[:space:]]*[:=][[:space:]]*[^[:space:]\"']{8,}" \
      "$file" || true
  )
done < <(git ls-files -z)

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
