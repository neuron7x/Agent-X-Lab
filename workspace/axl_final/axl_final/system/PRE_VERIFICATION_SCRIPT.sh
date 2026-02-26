#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build_proof

echo "[UDGS] Python syntax verification (core + adapters + engine + DAO-Arbiter)"
python -m py_compile udgs_core/*.py udgs_core/adapters/*.py engine/exoneural_governor/*.py tools/dao-arbiter/dao_lifebook/*.py

echo "[UDGS] STRICT_JSON sample packet validation (positive + negative paths)"
python -m udgs_core.cli validate-packet system/examples/packet.example.json

EXPECTED_PACKET_ANCHOR="$(python -m udgs_core.cli packet-anchor system/examples/packet.example.json)"
ACTUAL_PACKET_ANCHOR="$(python - <<'PY'
import json
with open('system/examples/packet.example.json', 'r', encoding='utf-8') as f:
    print(json.load(f)['SHA256_ANCHOR'])
PY
)"
[[ "$EXPECTED_PACKET_ANCHOR" == "$ACTUAL_PACKET_ANCHOR" ]]

for bad_packet in \
  system/examples/packet.invalid.anchor_mismatch.json \
  system/examples/packet.invalid.extra_key.json \
  system/examples/packet.invalid.missing_signals.json
do
  if python -m udgs_core.cli validate-packet "$bad_packet" >/dev/null 2>&1; then
    echo "[UDGS] ERROR: invalid packet unexpectedly passed: $bad_packet" >&2
    exit 1
  fi
done

echo "[UDGS] SYSTEM_OBJECT build + anchor generation"
python -m udgs_core.cli build-system-object --root . --config system/udgs.config.json --out SYSTEM_OBJECT.json
python -m udgs_core.cli anchor SYSTEM_OBJECT.json > build_proof/system_object.sha256

echo "[UDGS] UI contract static checks (fail-closed semantics)"
python build_proof/scripts/check_ui_contract.py

echo "[UDGS] Engine smoke tests (CI-lite, plugin autoload disabled)"
(
  cd engine
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q     tests/test_backend.py     tests/test_network_backend.py     tests/test_doctor.py::test_quickstart_script_exists_and_executable
)

# DAO-Arbiter tests require dev dependencies (for example hypothesis).
# Enable this block in CI or a prepared local environment:
# (
#   cd tools/dao-arbiter
#   python -m pip install -e ".[dev]"
#   python -m pytest -q dao_lifebook/tests.py
# )

echo "[UDGS] Pre-verification script completed"

echo "[UDGS QA8] UDGS Core test suite"
python -m pytest udgs_core/tests/ -q

echo "[UDGS QA8] QA8 autonomous audit single cycle"
python -m udgs_core.cli qa8-heal --root . 2>/dev/null | python -c "
import json, sys
d = json.load(sys.stdin)
assert d['mode'] == 'NOMINAL', f'QA8 not NOMINAL: {d[\"mode\"]}'
assert d['baseline_anchor'] == d['live_anchor'], 'Anchor mismatch'
print(f'[UDGS QA8] QA8 mode={d[\"mode\"]}  anchor={d[\"baseline_anchor\"][:16]}...')
"

echo "[UDGS QA8] Pre-verification COMPLETE — QA8 grade confirmed"
