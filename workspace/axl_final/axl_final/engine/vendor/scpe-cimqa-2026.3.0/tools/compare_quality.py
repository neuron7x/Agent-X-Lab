#!/usr/bin/env python3
import argparse, json, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def write(p: Path, obj: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

ap = argparse.ArgumentParser()
ap.add_argument("--baseline", default="REPORTS/quality-baseline.json")
ap.add_argument("--after", default="REPORTS/quality-after.json")
ap.add_argument("--delta", default="REPORTS/delta.json")
ap.add_argument("--summary", default="REPORTS/diff-summary.json")
args = ap.parse_args()

root = Path(".").resolve()
b = root / args.baseline
a = root / args.after

b_sha = sha256_file(b) if b.exists() else "MISSING"
a_sha = sha256_file(a) if a.exists() else "MISSING"

sb = load(root / "REPORTS/scorecard.json", default={})
sa = load(root / "REPORTS/scorecard.after.json", default={})

score_delta = None
if isinstance(sb, dict) and isinstance(sa, dict):
    if "score" in sb and "score" in sa:
        score_delta = int(sa["score"]) - int(sb["score"])

contract_equal = False
if b.exists() and a.exists():
    bb = load(b, default={})
    aa = load(a, default={})
    contract_equal = (bb.get("contract") == aa.get("contract"))

out = {
  "baseline_sha": b_sha,
  "after_sha": a_sha,
  "score_delta": score_delta,
  "dimension_deltas": {},
  "metric_deltas": {},
  "measurement_contract_equal": bool(contract_equal)
}
write(root / args.delta, out)
write(root / args.summary, {"ok": True, "notes": "diff summary placeholder"})
print("ok")
