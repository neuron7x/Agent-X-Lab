#!/usr/bin/env python3
import argparse, json, os, shutil, subprocess, time, yaml
from pathlib import Path

def run_shell(cmd: str):
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def which(tool: str) -> bool:
    return shutil.which(tool) is not None

def now_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

ap = argparse.ArgumentParser()
ap.add_argument("--qm", default="QM.yml")
ap.add_argument("--out", default="REPORTS/quality-baseline.json")
ap.add_argument("--label", default="baseline", choices=["baseline", "after"])
args = ap.parse_args()

root = Path(".").resolve()
qm = yaml.safe_load((root / args.qm).read_text(encoding="utf-8"))
(root / "REPORTS" / "quality").mkdir(parents=True, exist_ok=True)

contract = qm.get("measurement_contract", {})
reports = contract.get("reports", []) or []

suite = {
  "utc": now_utc(),
  "label": args.label,
  "schema_version": qm.get("schema_version"),
  "contract": {"reports": reports},
  "tools_missing": [],
  "notes": []
}

# Deterministic: always emit each report file with the expected top-level keys.
# When tool is missing, emit a sentinel that fails downstream gates.

def write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# Lint
lint = {"lint": {"error_count": 999999, "tool": None, "tool_missing": True, "raw": None}}
for cand in (qm.get("runners", {}) or {}).get("lint", {}).get("prefer", []) or []:
    tool = cand.get("tool")
    cmd = cand.get("cmd")
    if tool and cmd and which(tool):
        rc, so, se = run_shell(cmd)
        lint = {"lint": {"error_count": 0 if rc == 0 else 1, "tool": tool, "tool_missing": False, "raw": {"rc": rc, "stderr": se[-2000:], "stdout": so[-2000:]}}}
        break
write_json(root / "REPORTS/quality/lint.json", lint)
if lint["lint"]["tool_missing"]:
    suite["tools_missing"].append("lint")

# Tests
tests = {"tests": {"fail_count": 999999, "tool": None, "tool_missing": True, "raw": None}}
for cand in (qm.get("runners", {}) or {}).get("tests", {}).get("prefer", []) or []:
    tool = cand.get("tool")
    cmd = cand.get("cmd")
    if tool and cmd and which(tool):
        rc, so, se = run_shell(cmd)
        tests = {"tests": {"fail_count": 0 if rc == 0 else 1, "tool": tool, "tool_missing": False, "raw": {"rc": rc, "stderr": se[-2000:], "stdout": so[-2000:]}}}
        break
write_json(root / "REPORTS/quality/tests.json", tests)
if tests["tests"]["tool_missing"]:
    suite["tools_missing"].append("tests")

# Security
security = {"security": {"high_count": 999999, "tool": None, "tool_missing": True, "raw": None}}
for cand in (qm.get("runners", {}) or {}).get("security", {}).get("prefer", []) or []:
    tool = cand.get("tool")
    cmd = cand.get("cmd")
    if tool and cmd and which(tool):
        rc, so, se = run_shell(cmd)
        # bandit json parsing is optional; deterministic minimal: rc==0 => 0
        security = {"security": {"high_count": 0 if rc == 0 else 1, "tool": tool, "tool_missing": False, "raw": {"rc": rc, "stderr": se[-2000:], "stdout": so[-2000:]}}}
        break
write_json(root / "REPORTS/quality/security.json", security)
if security["security"]["tool_missing"]:
    suite["tools_missing"].append("security")

# Maintainability (synthetic placeholders)
maint = {
  "complexity": {"p95": 999999},
  "duplication": {"lines": 999999},
  "tool_missing": True,
  "notes": ["placeholder: populate via your maintainability toolchain"]
}
write_json(root / "REPORTS/quality/maintainability.json", maint)

# Docs (synthetic placeholders)
docs = {"docs": {"broken_links": 999999, "tool_missing": True, "notes": ["placeholder: populate via docs toolchain"]}}
write_json(root / "REPORTS/quality/docs.json", docs)

# Perf (synthetic placeholders)
perf = {"perf": {"regression_detected": True, "tool_missing": True, "notes": ["placeholder: populate via perf toolchain"]}}
write_json(root / "REPORTS/quality/perf.json", perf)

write_json(Path(args.out), suite)
print("ok")
