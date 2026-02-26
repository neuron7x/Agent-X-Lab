"""Static checks for AXL-UI contract markers — QA8 aware."""
import sys
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_MARKERS = [
    "RATE_LIMITED",
    "halt_polling_until_reset",
    "show_countdown",
    "animate_only_in_state",
]

QA8_REQUIRED_MARKERS = ["qa8", "QA8"]

CHECKS_PASS = True


def check(label, condition, detail=""):
    global CHECKS_PASS
    status = "PASS" if condition else "MISS"
    msg = f"[UI_CONTRACT] {status}  {label}"
    if detail and not condition:
        msg += f"  ({detail})"
    print(msg)
    if not condition:
        CHECKS_PASS = False


try:
    config_path = os.path.join(ROOT, "system", "udgs.config.json")
    with open(config_path) as f:
        config = json.load(f)
except Exception as e:
    print(f"[UI_CONTRACT] ERROR reading udgs.config.json: {e}")
    sys.exit(2)

config_text = json.dumps(config)

try:
    i18n_text = open(os.path.join(ROOT, "src", "lib", "i18n.ts")).read()
except Exception as e:
    print(f"[UI_CONTRACT] ERROR reading i18n.ts: {e}")
    sys.exit(2)

for marker in REQUIRED_MARKERS:
    check(f"config contains '{marker}'", marker in config_text)

for marker in QA8_REQUIRED_MARKERS:
    check(f"config QA8 marker '{marker}'", marker in config_text)

check("i18n UA strings present", "ua:" in i18n_text)
check("i18n EN strings present", "en:" in i18n_text)
check("i18n RATE_LIMITED reference", "RATE_LIMITED" in i18n_text or "rateLimit" in i18n_text)
check("config qa8.enabled = true", config.get("qa8", {}).get("enabled") is True)
check("config excludes qa8_state/", "qa8_state/" in config.get("audit_exclude_rel_prefixes", []))
check("config grade = QA8", config.get("grade", "").startswith("QA8"))

print()
print(f"[UI_CONTRACT] FINAL_STATUS={'PASS' if CHECKS_PASS else 'FAIL'}")
sys.exit(0 if CHECKS_PASS else 1)
