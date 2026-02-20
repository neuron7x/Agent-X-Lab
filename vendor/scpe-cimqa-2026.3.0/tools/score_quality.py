#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import yaml

def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

ap = argparse.ArgumentParser()
ap.add_argument("qm", default="QM.yml")
ap.add_argument("--out", required=True)
args = ap.parse_args()

root = Path(".").resolve()
qm = yaml.safe_load((root / args.qm).read_text(encoding="utf-8"))
thr = (qm.get("thresholds") or {})
min_score = int(qm.get("min_score", 0) or 0)

lint = load_json(root / "REPORTS/quality/lint.json", default={"lint": {"error_count": 999999}})
tests = load_json(root / "REPORTS/quality/tests.json", default={"tests": {"fail_count": 999999}})
sec = load_json(root / "REPORTS/quality/security.json", default={"security": {"high_count": 999999}})
maint = load_json(root / "REPORTS/quality/maintainability.json", default={"complexity": {"p95": 999999}, "duplication": {"lines": 999999}})
docs = load_json(root / "REPORTS/quality/docs.json", default={"docs": {"broken_links": 999999}})
perf = load_json(root / "REPORTS/quality/perf.json", default={"perf": {"regression_detected": True}})

facts = {
  "lint.error_count": int(((lint.get("lint") or {}).get("error_count") or 999999)),
  "tests.fail_count": int(((tests.get("tests") or {}).get("fail_count") or 999999)),
  "security.high_count": int(((sec.get("security") or {}).get("high_count") or 999999)),
  "complexity.p95": float(((maint.get("complexity") or {}).get("p95") or 999999)),
  "duplication.lines": int(((maint.get("duplication") or {}).get("lines") or 999999)),
  "docs.broken_links": int(((docs.get("docs") or {}).get("broken_links") or 999999)),
  "perf.regression_detected": bool(((perf.get("perf") or {}).get("regression_detected") is True))
}

hard_blockers = {
  "lint": facts["lint.error_count"] == 0,
  "tests": facts["tests.fail_count"] == 0,
  "security": facts["security.high_count"] == 0
}

# Deterministic scoring: start at 100 and subtract capped penalties.
score = 100
score -= 30 if not hard_blockers["tests"] else 0
score -= 30 if not hard_blockers["security"] else 0
score -= 20 if not hard_blockers["lint"] else 0

p95_max = float(thr.get("complexity.p95_max", 25))
dup_max = int(thr.get("duplication.max_lines", 200))

if facts["complexity.p95"] > p95_max:
    score -= 10
if facts["duplication.lines"] > dup_max:
    score -= 5
if facts["docs.broken_links"] > 0:
    score -= 3
if facts["perf.regression_detected"]:
    score -= 2

score = clamp(int(score), 0, 100)

# CI summary is derived from REPORTS/checks.json when present; else fail-closed.
checks = load_json(root / "REPORTS/checks.json", default=None)
ci_required_failed = 999999
if isinstance(checks, dict):
    # GitHub check-runs API shape varies; deterministic: count non-success in check_runs.
    runs = checks.get("check_runs") or []
    if isinstance(runs, list) and runs:
        bad = 0
        for r in runs:
            conc = (r.get("conclusion") or "").lower()
            if conc not in ("success", "neutral"):
                bad += 1
        ci_required_failed = bad
    else:
        ci_required_failed = 0

scorecard = {
  "schema_version": "SCORECARD-2026.3",
  "min_score": min_score,
  "score": score,
  "dimensions": {
    "lint": {"error_count": facts["lint.error_count"]},
    "tests": {"fail_count": facts["tests.fail_count"]},
    "security": {"high_count": facts["security.high_count"]},
    "maintainability": {
      "complexity": {"p95": facts["complexity.p95"], "p95_max": p95_max},
      "duplication": {"lines": facts["duplication.lines"], "max_lines": dup_max}
    },
    "docs": {"broken_links": facts["docs.broken_links"]},
    "perf": {"regression_detected": facts["perf.regression_detected"]},
    "ci": {"required_checks_failed": ci_required_failed}
  },
  "hard_blockers": hard_blockers
}

outp = Path(args.out)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
