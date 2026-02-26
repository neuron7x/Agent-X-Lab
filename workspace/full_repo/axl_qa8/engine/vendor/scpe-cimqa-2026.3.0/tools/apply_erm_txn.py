#!/usr/bin/env python3
import argparse, json, subprocess, hashlib, yaml
from pathlib import Path

def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def must(cond, msg):
    if not cond:
        raise SystemExit(msg)

ap = argparse.ArgumentParser()
ap.add_argument("--erm", default="ERM.yml")
ap.add_argument("--txn", default="REPORTS/erm-txn.selected.yml")
ap.add_argument("--out", default="REPORTS/erm-patch.result.json")
ap.add_argument("--shadow-root", default=".scpe-shadow")
ap.add_argument("--branch-prefix", default="meta/erm")
args = ap.parse_args()

root = Path(".").resolve()
erm = yaml.safe_load((root / args.erm).read_text(encoding="utf-8"))
txn = yaml.safe_load((root / args.txn).read_text(encoding="utf-8"))

allow = set(erm.get("ssot_patch_allowlist", []))
patches = txn.get("patches", []) or []
ops = txn.get("ops", []) or []

dfp = txn.get("deadlock_fingerprint", "NO_MATCH")
base_sha = (txn.get("base_ssot") or {}).get("git_sha", "UNKNOWN")
work_id = "erm-" + sha256_text(f"{base_sha}|{dfp}")[:12]

shadow_root = root / args.shadow_root / work_id
branch = f"{args.branch_prefix}/{work_id}"

shadow_root.parent.mkdir(parents=True, exist_ok=True)
must(not shadow_root.exists(), f"shadow_worktree_exists:{shadow_root}")

rc, _, se = run(["git", "worktree", "add", "-b", branch, str(shadow_root), base_sha])
must(rc == 0, f"git_worktree_add_failed:{se.strip()}")

result = {
  "work_id": work_id,
  "deadlock_fingerprint": dfp,
  "shadow_root": str(shadow_root),
  "shadow_branch": branch,
  "applied": [],
  "skipped": [],
  "status": "UNKNOWN"
}

for op in ops:
    t = op.get("type")
    if t == "hard_revert_ssot":
        result["status"] = "HARD_REVERT_REQUIRED"
        outp = root / args.out
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("ok")
        raise SystemExit(0)
    must(t == "patch_file", f"unsupported_op_type:{t}")

for p in patches:
    path = p.get("path")
    diff = p.get("unified_diff", "")
    must(path in allow, f"patch.path.not_allowed:{path}")
    diff_sha = p.get("unified_diff_sha256", "")
    must(diff_sha == sha256_text(diff), f"patch.diff_sha256.mismatch:{path}")

    tmp = shadow_root / ".scpe.tmp.diff"
    tmp.write_text(diff, encoding="utf-8")
    rc, _, se = run(["git", "apply", str(tmp)], cwd=str(shadow_root))
    must(rc == 0, f"git_apply_failed:{path}:{se.strip()}")
    result["applied"].append(path)

rc, so, se = run(["git", "status", "--porcelain"], cwd=str(shadow_root))
must(rc == 0, f"git_status_failed:{se.strip()}")
changed = []
for line in so.splitlines():
    if len(line) >= 4:
        changed.append(line[3:].strip())
for c in changed:
    must(c in allow, f"shadow_changed_non_allowlisted:{c}")

rc, _, se = run(["git", "add", "-A"], cwd=str(shadow_root))
must(rc == 0, f"git_add_failed:{se.strip()}")
rc, _, se = run(["git", "commit", "-m", f"chore(meta): apply ERM txn {txn.get('txn_id', 'UNKNOWN')} ({dfp})"], cwd=str(shadow_root))
must(rc == 0, f"git_commit_failed:{se.strip()}")

rc, so, se = run(["git", "rev-parse", "HEAD"], cwd=str(shadow_root))
must(rc == 0, f"git_rev_parse_failed:{se.strip()}")
result["shadow_head_sha"] = so.strip()
result["status"] = "PATCH_APPLIED"

outp = root / args.out
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
