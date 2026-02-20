#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, time, os

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect(root: pathlib.Path):
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        out.append({"path": str(p.relative_to(root)), "sha256": sha256_file(p)})
    return out

ap = argparse.ArgumentParser()
ap.add_argument("--evidence-root", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--deadlock-fingerprint-path", default="REPORTS/deadlock.json")
ap.add_argument("--erm-txn-path", default="REPORTS/erm-txn.selected.yml")
ap.add_argument("--ssot-root-primary", default=".")
ap.add_argument("--ssot-root-shadow", default=".scpe-shadow")
args = ap.parse_args()

root = pathlib.Path(args.evidence_root).resolve()
meta_root = root / "META"
meta_root.mkdir(parents=True, exist_ok=True)

primary = pathlib.Path(args.ssot_root_primary).resolve()
deadlock = json.load(open(primary / args.deadlock_fingerprint_path, "r", encoding="utf-8")) if (primary / args.deadlock_fingerprint_path).exists() else {}
erm_txn_id = "UNKNOWN"
if (primary / args.erm_txn_path).exists():
    txt = (primary / args.erm_txn_path).read_text(encoding="utf-8", errors="replace")
    for line in txt.splitlines():
        if line.strip().startswith("txn_id:"):
            erm_txn_id = line.split(":", 1)[1].strip().strip("'\"")
            break

ssot_files = ["PA.txt", "IM.yml", "QM.yml", "GM.yml", "CG.json", "OH.yml", "ERM.yml", "PL.json"]
ssot_before = {}
for f in ssot_files:
    p = primary / f
    if p.exists():
        ssot_before[f] = sha256_file(p)

shadow_root = (primary / args.ssot_root_shadow).resolve()
shadow_dirs = sorted([d for d in shadow_root.iterdir() if d.is_dir()], key=lambda p: p.name) if shadow_root.exists() else []
ssot_after = {}
if shadow_dirs:
    sh = shadow_dirs[-1]
    for f in ssot_files:
        p = sh / f
        if p.exists():
            ssot_after[f] = sha256_file(p)

inv_check = primary / "REPORTS" / "invariants.check.json"
inv = json.load(open(inv_check, "r", encoding="utf-8")) if inv_check.exists() else {}

manifest = {
  "work_id": root.name,
  "utc_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "git_sha_before": os.environ.get("GIT_BEFORE", "UNKNOWN"),
  "git_sha_after": os.environ.get("GIT_AFTER", "UNKNOWN"),
  "deadlock_fingerprint": deadlock.get("deadlock_fingerprint", "UNKNOWN"),
  "erm_txn_id": erm_txn_id,
  "ssot_sha256_before": ssot_before,
  "ssot_sha256_after": ssot_after,
  "invariants_sha256_before": inv.get("invariants_sha256_before", "UNKNOWN"),
  "invariants_sha256_after": inv.get("invariants_sha256_after", "UNKNOWN"),
  "commands": [],
  "proofs": collect(meta_root)
}

outp = pathlib.Path(args.out).resolve()
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
