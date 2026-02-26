#!/usr/bin/env python3
import argparse, hashlib, os, subprocess, yaml, json
from pathlib import Path

SSOT_FILES = ["PA.txt", "IM.yml", "QM.yml", "GM.yml", "CG.json", "OH.yml", "ERM.yml", "PL.json"]

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git_head_sha() -> str:
    rc, so, _ = run(["git", "rev-parse", "HEAD"])
    if rc != 0:
        return "UNKNOWN"
    return so.strip()

def ssot_sha256_map(repo_root: Path) -> dict:
    out = {}
    for f in SSOT_FILES:
        p = repo_root / f
        if p.exists():
            out[f] = sha256_file(p)
    return out

def pick_recipe(erm: dict, deadlock_fingerprint: str) -> dict:
    for r in (erm.get("recipes") or []):
        sel = (r.get("selector") or {})
        if sel.get("type") == "exact_deadlock_fingerprint" and sel.get("value") == deadlock_fingerprint:
            return r
    for r in (erm.get("recipes") or []):
        sel = (r.get("selector") or {})
        if sel.get("type") == "exact_deadlock_fingerprint" and sel.get("value") == "NO_MATCH":
            return r
    return {"recipe_id": "ERM.RCP.000", "action": "hard_revert_ssot", "reason": "no recipe match; entropy forbidden"}

def fill_patch_sha256(patches: list) -> list:
    out = []
    for p in patches:
        p2 = dict(p)
        diff = p2.get("unified_diff", "")
        if p2.get("unified_diff_sha256") == "TBD_BY_TOOL":
            p2["unified_diff_sha256"] = sha256_text(diff)
        out.append(p2)
    return out

ap = argparse.ArgumentParser()
ap.add_argument("--erm", default="ERM.yml")
ap.add_argument("--deadlock", default="REPORTS/deadlock.json")
ap.add_argument("--out", default="REPORTS/erm-txn.selected.yml")
args = ap.parse_args()

root = Path(".").resolve()
erm = yaml.safe_load((root / args.erm).read_text(encoding="utf-8"))
dead = json.loads((root / args.deadlock).read_text(encoding="utf-8", errors="replace"))
dfp = dead.get("deadlock_fingerprint", "NO_MATCH")

recipe = pick_recipe(erm, dfp)

base = {
  "git_sha": os.environ.get("GIT_BEFORE") or git_head_sha(),
  "ssot_sha256_map": ssot_sha256_map(root)
}

txn = {
  "txn_id": "ERM.TXN.000",
  "base_ssot": base,
  "deadlock_fingerprint": dfp,
  "ops": [],
  "patches": [],
  "expected_outputs": {
    "ssot_sha256_map_after": {},
    "meta_gates_expected": ["G.META.001", "G.META.002", "G.META.003"]
  }
}

if recipe.get("action") == "hard_revert_ssot":
    txn["ops"] = [{"op_id": "OP.000", "type": "hard_revert_ssot", "target_path": "SSOT", "preconditions": [], "postconditions": ["ssot_restored"]}]
    txn["expected_outputs"]["ssot_sha256_map_after"] = base["ssot_sha256_map"]
else:
    tmpl = recipe.get("txn_template") or {}
    txn["txn_id"] = tmpl.get("txn_id", txn["txn_id"])
    txn["ops"] = tmpl.get("ops", [])
    txn["patches"] = fill_patch_sha256(tmpl.get("patches", []))

outp = root / args.out
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(yaml.safe_dump(txn, sort_keys=False), encoding="utf-8")
print("ok")
