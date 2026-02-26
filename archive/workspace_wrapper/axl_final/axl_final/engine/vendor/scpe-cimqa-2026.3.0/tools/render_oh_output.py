#!/usr/bin/env python3
import argparse, json, time
from pathlib import Path
import yaml

def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def maybe(p: Path):
    return p.as_posix() if p.exists() else None

ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="strict")
ap.add_argument("--repo", default="UNKNOWN")
ap.add_argument("--base-branch", default="UNKNOWN")
ap.add_argument("--work-id", default="work")
ap.add_argument("--out", default="OH-output.yml")
args = ap.parse_args()

root = Path(".").resolve()
inv = load_json(root / "REPORTS/inventory.json", default={})
sc = load_json(root / "REPORTS/scorecard.json", default={})
delta = load_json(root / "REPORTS/delta.json", default={})
dead = load_json(root / "REPORTS/deadlock.json", default={})
gd = load_json(root / "REPORTS/gate-decisions.after.json", default=load_json(root / "REPORTS/gate-decisions.json", default={}))
interp = load_json(root / "REPORTS/interpretation.json", default={})
meta = load_json(root / "REPORTS/meta-validity.json", default={})

out = {
  "header": {
    "name": "Codex Interpreted Mechanized Quality Agent",
    "version": "2026.3.0",
    "mode": args.mode,
    "work_id": args.work_id,
    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "repo": args.repo,
    "base_branch": args.base_branch,
    "git_sha_before": inv.get("git_head", "UNKNOWN"),
    "git_sha_after": inv.get("git_head", "UNKNOWN")
  },
  "inputs": {
    "missing_required": [],
    "assumptions": [],
    "constraints": {}
  },
  "scope": {
    "allowlist": [],
    "exclusions": [],
    "budgets": {}
  },
  "modalities": {
    "present": interp.get("modalities_present", []),
    "missing": interp.get("modalities_missing", []),
    "instrumentation_required": interp.get("instrumentation_required", [])
  },
  "interpretation": {
    "status": interp.get("status", "UNKNOWN"),
    "items": interp.get("items", []),
    "contradictions": interp.get("contradictions", {}),
    "alternatives": interp.get("alternatives", {}),
    "trace_path": interp.get("trace_path", "REPORTS/trace.jsonl")
  },
  "scorecard": {
    "score": sc.get("score"),
    "min_score": sc.get("min_score"),
    "dimensions": sc.get("dimensions", {}),
    "hard_blockers": sc.get("hard_blockers", {})
  },
  "delta": {
    "baseline_sha": delta.get("baseline_sha"),
    "after_sha": delta.get("after_sha"),
    "score_delta": delta.get("score_delta"),
    "dimension_deltas": delta.get("dimension_deltas", {}),
    "metric_deltas": delta.get("metric_deltas", {}),
    "measurement_contract_equal": delta.get("measurement_contract_equal")
  },
  "deadlock": {
    "consecutive_fails": dead.get("consecutive_fails"),
    "deficit_severity": dead.get("deficit_severity"),
    "deadlock_fingerprint": dead.get("deadlock_fingerprint"),
    "category": dead.get("category"),
    "owned_fail_gates": dead.get("owned_fail_gates"),
    "missing_reports_count": dead.get("missing_reports_count")
  },
  "meta": {
    "erm_triggered": bool(load_json(root / "REPORTS/meta-state.json", default={}).get("erm_trigger_true")),
    "erm_txn_id": None,
    "meta_gates": {},
    "shadow_branch": None,
    "manifest_meta_path": maybe(root / "MANIFEST.META.json"),
    "meta_pr_url": None
  },
  "gate_decisions": {
    "owned_gates": (gd.get("owned_gates") if isinstance(gd, dict) else {})
  },
  "pr": {
    "pr_url": None,
    "pr_number": None,
    "head_branch": None,
    "head_sha": None,
    "state": None
  },
  "ci": {
    "run_urls": [],
    "checks_summary": {}
  },
  "actions": {
    "act_performed": [],
    "diff_summary": None,
    "commit_list": [],
    "deficits_closed": [],
    "ordered_plan": []
  },
  "evidence": {
    "evidence_root": None,
    "manifest_path": maybe(root / "MANIFEST.json"),
    "reports_index": "REPORTS/",
    "artifacts_sha256_count": None,
    "redaction_policy_path": "SECURITY.redaction.yml"
  },
  "rollback": {
    "revert_strategy": "git revert commits OR close PR without merge",
    "revert_command_or_steps": "git revert <sha> OR gh pr close <n> --delete-branch"
  },
  "next_steps": {
    "blocking_items": [],
    "instrumentation_plan": [],
    "handoff": []
  }
}

# Preserve OH ordering
oh = yaml.safe_load((root / "OH.yml").read_text(encoding="utf-8"))
order = oh.get("output_order") or []
ordered = {}
for k in order:
    ordered[k] = out.get(k)

Path(args.out).write_text(yaml.safe_dump(ordered, sort_keys=False), encoding="utf-8")
print("ok")
