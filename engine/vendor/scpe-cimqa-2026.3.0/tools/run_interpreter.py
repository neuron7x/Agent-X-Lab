#!/usr/bin/env python3
import argparse, hashlib, json, os, time
from pathlib import Path
import yaml

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def write_json(p: Path, obj: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def missing_any_reports(modalities, root: Path):
    missing = []
    for m in modalities:
        for r in (m.get("required_reports") or []):
            if not (root / r).exists():
                missing.append(r)
    return sorted(set(missing))

ap = argparse.ArgumentParser()
ap.add_argument("--im", default="IM.yml")
ap.add_argument("--qm", default="QM.yml")
ap.add_argument("--baseline", default="REPORTS/quality-baseline.json")
ap.add_argument("--out", default="REPORTS/interpretation.json")
ap.add_argument("--trace", default="REPORTS/trace.jsonl")
args = ap.parse_args()

root = Path(".").resolve()
im = yaml.safe_load((root / args.im).read_text(encoding="utf-8"))
qm = yaml.safe_load((root / args.qm).read_text(encoding="utf-8"))
thr = (qm.get("thresholds") or {})

# Facts are read from quality reports; if missing, default fail-closed.
scorecard = load_json(root / "REPORTS/scorecard.json", default=None)
if scorecard is None:
    # best-effort: compute quickly from existing reports
    os.system("python3 tools/score_quality.py QM.yml --out REPORTS/scorecard.json >/dev/null 2>&1")
    scorecard = load_json(root / "REPORTS/scorecard.json", default={})

dims = (scorecard.get("dimensions") or {})

facts = {
  "tests.fail_count": int(((dims.get("tests") or {}).get("fail_count") or 999999)),
  "security.high_count": int(((dims.get("security") or {}).get("high_count") or 999999)),
  "lint.error_count": int(((dims.get("lint") or {}).get("error_count") or 999999)),
  "complexity.p95": float((((dims.get("maintainability") or {}).get("complexity") or {}).get("p95") or 999999)),
  "duplication.lines": int((((dims.get("maintainability") or {}).get("duplication") or {}).get("lines") or 999999)),
  "docs.broken_links": int(((dims.get("docs") or {}).get("broken_links") or 999999)),
  "perf.regression_detected": bool(((dims.get("perf") or {}).get("regression_detected") is True))
}

def threshold(key: str):
    return thr.get(key)

modalities = im.get("modalities") or []
missing_reports = missing_any_reports(modalities, root)

items = []
trace_lines = []
step = 0

def trace(rule_id, decision, outputs):
    global step
    step += 1
    snap = sha256_text(json.dumps({"facts": facts, "thresholds": thr}, sort_keys=True, separators=(",", ":")))
    rec = {"step": step, "rule_id": rule_id, "decision": decision, "facts_snapshot_sha256": snap, "outputs": outputs}
    trace_lines.append(json.dumps(rec, sort_keys=True))

# Apply rules in listed order; only one item per rule when condition true.
for rule in (im.get("interpreted_rules") or []):
    rid = rule.get("id")
    prio = int(rule.get("priority") or 0)
    cond = rule.get("if") or ""

    fired = False
    if cond == "missing_any_reports(modalities)":
        fired = len(missing_reports) > 0
        if fired:
            then = (rule.get("then") or {})
            it = (then.get("interpretation_item") or {})
            item = dict(it)
            item["priority"] = prio
            item["value"] = missing_reports
            items.append(item)
            inst = (then.get("instrumentation_required") or [])
            trace(rid, "FIRE", {"missing_reports": missing_reports, "instrumentation_required": inst})
    elif cond.startswith("fact('tests.fail_count')"):
        fired = facts["tests.fail_count"] > 0
    elif cond.startswith("fact('security.high_count')"):
        fired = facts["security.high_count"] > 0
    elif cond.startswith("fact('lint.error_count')"):
        fired = facts["lint.error_count"] > 0
    elif cond.startswith("fact('complexity.p95')"):
        mx = float(threshold("complexity.p95_max") or 0)
        fired = facts["complexity.p95"] > mx
    elif cond.startswith("fact('duplication.lines')"):
        mx = int(threshold("duplication.max_lines") or 0)
        fired = facts["duplication.lines"] > mx
    elif cond.startswith("fact('docs.broken_links')"):
        fired = facts["docs.broken_links"] > 0
    elif cond.startswith("fact('perf.regression_detected')"):
        fired = facts["perf.regression_detected"] is True

    if fired and cond != "missing_any_reports(modalities)":
        then = (rule.get("then") or {})
        it = (then.get("interpretation_item") or {})
        item = dict(it)
        item["priority"] = prio
        # value already defined as expression strings; keep literal for trace; downstream does not eval.
        items.append(item)
        trace(rid, "FIRE", {"condition": cond})

# Determine overall status
statuses = [x.get("status") for x in items]
overall = "PASS"
if "FAIL" in statuses:
    overall = "FAIL"
elif "UNKNOWN" in statuses:
    overall = "UNKNOWN"

present_modalities = []
missing_modalities = []
for m in modalities:
    mid = m.get("id")
    req = (m.get("required_reports") or [])
    if all((root / r).exists() for r in req):
        present_modalities.append(mid)
    else:
        missing_modalities.append(mid)

instrumentation_required = []
for x in items:
    if x.get("metric") == "missing_reports":
        instrumentation_required = ["emit_quality_reports", "emit_trace", "emit_meta_state"]

out = {
  "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "status": overall,
  "items": items,
  "instrumentation_required": instrumentation_required,
  "modalities_present": present_modalities,
  "modalities_missing": missing_modalities,
  "contradictions": {"status": "NONE", "path": "REPORTS/contradictions.json"},
  "alternatives": {"status": "NONE", "path": "REPORTS/alternatives.json"},
  "trace_path": args.trace
}

write_json(root / args.out, out)
Path(args.trace).parent.mkdir(parents=True, exist_ok=True)
Path(args.trace).write_text("\n".join(trace_lines) + ("\n" if trace_lines else ""), encoding="utf-8")

# Stub contradiction/alternatives files deterministically
write_json(root / "REPORTS/contradictions.json", {"ok": True, "notes": "no engine executed"})
write_json(root / "REPORTS/alternatives.json", {"ok": True, "notes": "no engine executed"})

print("ok")
