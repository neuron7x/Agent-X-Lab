#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def must(cond, msg, errs):
    if not cond:
        errs.append(msg)

ap = argparse.ArgumentParser()
ap.add_argument("interpretation")
ap.add_argument("--out", default="REPORTS/interpretation.schema-check.json")
args = ap.parse_args()

p = Path(args.interpretation)
errs = []
must(p.exists(), f"missing:{args.interpretation}", errs)
obj = {}
if p.exists():
    obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))

req = ["status", "items", "instrumentation_required", "modalities_present", "modalities_missing", "contradictions", "alternatives", "trace_path"]
for k in req:
    must(k in obj, f"missing_field:{k}", errs)

items = obj.get("items", [])
must(isinstance(items, list), "items.not_list", errs)

out = {"ok": len(errs) == 0, "errors": errs}
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok" if out["ok"] else "fail")
raise SystemExit(0 if out["ok"] else 2)
