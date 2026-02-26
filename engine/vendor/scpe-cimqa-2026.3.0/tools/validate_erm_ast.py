#!/usr/bin/env python3
import argparse, hashlib, json, os, yaml

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def must(cond, msg, errs):
    if not cond:
        errs.append(msg)

ap = argparse.ArgumentParser()
ap.add_argument("erm_spec")
ap.add_argument("txn")
ap.add_argument("--out", required=True)
args = ap.parse_args()

erm = yaml.safe_load(open(args.erm_spec, "r", encoding="utf-8"))
txn = yaml.safe_load(open(args.txn, "r", encoding="utf-8"))

errs = []
schema = erm.get("transaction_schema", {})
req = schema.get("required_fields", [])
for k in req:
    must(k in txn, f"missing:{k}", errs)

ops = txn.get("ops", [])
patches = txn.get("patches", [])
must(isinstance(ops, list) and len(ops) > 0, "ops.empty_or_not_list", errs)
must(isinstance(patches, list) and len(patches) > 0, "patches.empty_or_not_list", errs)

allow = set(erm.get("ssot_patch_allowlist", []))
for p in patches:
    must("path" in p, "patch.path.missing", errs)
    if "path" in p:
        must(p["path"] in allow, f"patch.path.not_allowed:{p['path']}", errs)
    must("unified_diff" in p, f"patch.diff.missing:{p.get('path','?')}", errs)
    must("unified_diff_sha256" in p, f"patch.diff_sha256.missing:{p.get('path','?')}", errs)
    if "unified_diff" in p and "unified_diff_sha256" in p:
        h = sha256_text(p["unified_diff"])
        if p["unified_diff_sha256"] == "TBD_BY_TOOL":
            pass
        else:
            must(h == p["unified_diff_sha256"], f"patch.diff_sha256.mismatch:{p.get('path','?')}", errs)

out = {
  "ast_ok": len(errs) == 0,
  "errors": errs,
  "txn_id": txn.get("txn_id"),
  "deadlock_fingerprint": txn.get("deadlock_fingerprint")
}
os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, sort_keys=True)
print("ok" if out["ast_ok"] else "fail")
raise SystemExit(0 if out["ast_ok"] else 2)
