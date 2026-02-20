#!/usr/bin/env python3
import argparse, json, os, platform, shutil, subprocess, time
from pathlib import Path

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def which(x):
    return shutil.which(x) or ""

ap = argparse.ArgumentParser()
ap.add_argument("--out-inventory", default="REPORTS/inventory.json")
ap.add_argument("--out-ci", default="REPORTS/ci-baseline.json")
ap.add_argument("--env", default="ENV.txt")
ap.add_argument("--commands", default="COMMANDS.txt")
args = ap.parse_args()

root = Path(".").resolve()
(root / "REPORTS").mkdir(parents=True, exist_ok=True)
(root / "REPORTS" / "signals").mkdir(parents=True, exist_ok=True)

rc, so, _ = run(["git", "rev-parse", "HEAD"])
head = so.strip() if rc == 0 else "UNKNOWN"

tools = {
  "git": which("git"),
  "gh": which("gh"),
  "python3": which("python3"),
  "jq": which("jq")
}

inv = {
  "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "platform": platform.platform(),
  "python": platform.python_version(),
  "cwd": str(root),
  "git_head": head,
  "tools": tools
}

Path(args.out_inventory).parent.mkdir(parents=True, exist_ok=True)
Path(args.out_inventory).write_text(json.dumps(inv, indent=2, sort_keys=True) + "\n", encoding="utf-8")

ci = {
  "utc": inv["utc"],
  "baseline": {
    "note": "capture with gh api in real run",
    "head": head
  }
}
Path(args.out_ci).parent.mkdir(parents=True, exist_ok=True)
Path(args.out_ci).write_text(json.dumps(ci, indent=2, sort_keys=True) + "\n", encoding="utf-8")

Path(args.env).write_text("".join([
  f"UTC={inv['utc']}\n",
  f"CWD={inv['cwd']}\n",
  f"GIT_HEAD={head}\n",
  f"PYTHON={inv['python']}\n"
]), encoding="utf-8")

Path(args.commands).write_text("# Commands executed by CIMQA\n", encoding="utf-8")
print("ok")
