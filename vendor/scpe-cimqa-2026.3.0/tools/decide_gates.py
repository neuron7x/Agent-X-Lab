#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import yaml

def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def gate_status_bool(b):
    return "PASS" if bool(b) else "FAIL"

ap = argparse.ArgumentParser()
ap.add_argument("--gm", default="GM.yml")
ap.add_argument("--out", default="REPORTS/gate-decisions.json")
args = ap.parse_args()

root = Path(".").resolve()
gm = yaml.safe_load((root / args.gm).read_text(encoding="utf-8"))
scorecard = load_json(root / "REPORTS/scorecard.json", default={})
interp = load_json(root / "REPORTS/interpretation.json", default={})
meta_valid = load_json(root / "REPORTS/meta-validity.json", default={})

owned = {}

# Helper values
missing_reports_count = 0
it_items = interp.get("items", []) or []
for x in it_items:
    if x.get("metric") == "missing_reports":
        v = x.get("value", [])
        if isinstance(v, list):
            missing_reports_count = len(v)

trace_lines = 0
trace_path = root / "REPORTS/trace.jsonl"
if trace_path.exists():
    trace_lines = len(trace_path.read_text(encoding="utf-8", errors="replace").splitlines())

# Evaluate known gates deterministically (subset of predicates).
for g in (gm.get("gates") or []):
    gid = g.get("id")
    if not gid:
        continue

    if gid == "G.SEC.001":
        owned[gid] = {"status": gate_status_bool((root / "SECURITY.redaction.yml").exists())}
    elif gid == "G.IM.001":
        ok = (root / "IM.yml").exists()
        if ok:
            im = yaml.safe_load((root / "IM.yml").read_text(encoding="utf-8"))
            ok = str(im.get("schema_version", "")).startswith("IM-2026.")
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.IM.010":
        ok = (root / "REPORTS/interpretation.json").exists() and (missing_reports_count == 0 or len(interp.get("instrumentation_required") or []) > 0)
        owned[gid] = {"status": gate_status_bool(ok), "missing_reports_count": missing_reports_count}
    elif gid == "G.IM.020":
        ok = trace_path.exists() and trace_lines > 0
        owned[gid] = {"status": gate_status_bool(ok), "trace_lines": trace_lines}
    elif gid == "G.IM.030":
        ok = (root / "REPORTS/delta.json").exists() and (root / "REPORTS/quality-baseline.json").exists() and (root / "REPORTS/quality-after.json").exists()
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.QM.001":
        req = [
          "REPORTS/quality-baseline.json",
          "REPORTS/quality/lint.json",
          "REPORTS/quality/tests.json",
          "REPORTS/quality/security.json",
          "REPORTS/quality/maintainability.json",
          "REPORTS/quality/docs.json",
          "REPORTS/quality/perf.json"
        ]
        ok = all((root / r).exists() for r in req)
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid in ("G.QM.010", "G.QM.020", "G.QM.030", "G.QM.040", "G.QM.050", "G.QM.060"):
        dims = (scorecard.get("dimensions") or {})
        hb = (scorecard.get("hard_blockers") or {})
        if gid == "G.QM.010":
            ok = bool(hb.get("lint")) and bool(hb.get("tests")) and bool(hb.get("security"))
        elif gid == "G.QM.020":
            m = dims.get("maintainability") or {}
            c = (m.get("complexity") or {})
            d = (m.get("duplication") or {})
            ok = float(c.get("p95", 999999)) <= float(c.get("p95_max", 0)) and int(d.get("lines", 999999)) <= int(d.get("max_lines", 0))
        elif gid == "G.QM.030":
            ok = int((dims.get("docs") or {}).get("broken_links", 999999)) == 0
        elif gid == "G.QM.040":
            ok = bool((dims.get("perf") or {}).get("regression_detected", True)) is False
        elif gid == "G.QM.050":
            ok = int((dims.get("ci") or {}).get("required_checks_failed", 999999)) == 0
        else:
            ok = int(scorecard.get("score", 0)) >= int(scorecard.get("min_score", 0))
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.META.001":
        ok = (root / "REPORTS/erm-txn.selected.yml").exists() and bool(((meta_valid.get("meta") or {}).get("ast_ok") is True))
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.META.002":
        ok = (root / "MANIFEST.META.json").exists() and bool(((meta_valid.get("meta") or {}).get("invariants_preserved") is True)) and int(((meta_valid.get("meta") or {}).get("regression_rate") or 1)) == 0
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.META.003":
        ok = bool(((meta_valid.get("meta") or {}).get("shadow_isolation_ok") is True))
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.CDX.PR.001":
        pr = load_json(root / "REPORTS/pr.json", default={})
        ok = bool(pr.get("url")) or bool(pr.get("pr_url"))
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.CDX.CI.001":
        ok = (root / "REPORTS/ci-after.json").exists() and (root / "REPORTS/checks.json").exists()
        owned[gid] = {"status": gate_status_bool(ok)}
    elif gid == "G.EBS.001":
        ok = (root / "MANIFEST.json").exists()
        owned[gid] = {"status": gate_status_bool(ok)}
    else:
        # Unknown gate id -> FAIL (fail-closed)
        owned[gid] = {"status": "FAIL", "reason": "unknown_gate_handler"}

out = {
  "utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
  "owned_gates": owned
}

outp = root / args.out
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
