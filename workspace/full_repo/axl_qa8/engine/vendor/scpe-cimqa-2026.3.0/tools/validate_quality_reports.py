#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import yaml

def must(cond, msg, errs):
    if not cond:
        errs.append(msg)

ap = argparse.ArgumentParser()
ap.add_argument("qm", nargs="?", default="QM.yml")
ap.add_argument("--out", default="REPORTS/quality.schema-check.json")
args = ap.parse_args()

root = Path(".").resolve()
qm = yaml.safe_load((root / args.qm).read_text(encoding="utf-8"))
reports = ((qm.get("measurement_contract") or {}).get("reports") or [])
errs = []

must((root / "REPORTS/quality-baseline.json").exists(), "missing:REPORTS/quality-baseline.json", errs)
for r in reports:
    p = (r.get("path") or "").strip()
    must(p != "", "contract.report.path.empty", errs)
    if p:
        must((root / p).exists(), f"missing:{p}", errs)

out = {"ok": len(errs) == 0, "errors": errs, "schema_version": qm.get("schema_version")}
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok" if out["ok"] else "fail")
raise SystemExit(0 if out["ok"] else 2)
