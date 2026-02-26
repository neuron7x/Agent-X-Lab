#!/usr/bin/env python3
import argparse, hashlib, json, os, time

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load(p):
    return json.load(open(p, "r", encoding="utf-8"))

ap = argparse.ArgumentParser()
ap.add_argument("--gate-decisions", required=True)
ap.add_argument("--interpretation", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--consecutive-fails", type=int, required=True)
args = ap.parse_args()

gd = load(args.gate_decisions)
it = load(args.interpretation)

items = it.get("items", [])
sev0 = [x for x in items if x.get("severity") == "S0"]
deficit_severity = "S0" if len(sev0) > 0 else "S1+"
category = sev0[0].get("category") if sev0 else (items[0].get("category") if items else "none")

owned = gd.get("owned_gates", gd.get("owned", gd))
owned_fail = []
if isinstance(owned, dict):
    for k, v in owned.items():
        if isinstance(v, dict) and v.get("status") == "FAIL":
            owned_fail.append(k)
elif isinstance(owned, list):
    for x in owned:
        if x.get("status") == "FAIL":
            owned_fail.append(x.get("id"))

missing_reports = []
for x in items:
    if x.get("metric") == "missing_reports":
        v = x.get("value", [])
        if isinstance(v, list):
            missing_reports = v

payload = {
  "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "consecutive_fails": args.consecutive_fails,
  "deficit_severity": deficit_severity,
  "category": category,
  "owned_fail_gates": sorted(set([g for g in owned_fail if g])),
  "missing_reports_count": len(missing_reports),
  "missing_reports": missing_reports
}

fingerprint_key = json.dumps({
  "deficit_severity": payload["deficit_severity"],
  "category": payload["category"],
  "owned_fail_gates": payload["owned_fail_gates"],
  "missing_reports": payload["missing_reports"]
}, sort_keys=True, separators=(",",":"))

if payload["missing_reports_count"] > 0 and payload["deficit_severity"] == "S0":
    fingerprint = "DFP:missing_reports"
else:
    fingerprint = "DFP:" + sha256_text(fingerprint_key)[:12]

payload["deadlock_fingerprint"] = fingerprint
os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
json.dump(payload, open(args.out, "w", encoding="utf-8"), indent=2, sort_keys=True)
print(payload["deadlock_fingerprint"])
