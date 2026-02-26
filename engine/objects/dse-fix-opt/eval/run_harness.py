#!/usr/bin/env python3
"""IOPS-2026 eval harness runner for this object.

Design goals:
  - fail-closed: any missing file/schema mismatch => FAIL
  - deterministic option: stable timestamp + stable evidence path for Git commits
  - dependency-light: stdlib only

Usage:
  python objects/dse-fix-opt/eval/run_harness.py --repo-root . \
    --cases objects/dse-fix-opt/eval/cases --write-evidence

Deterministic evidence (commit-friendly):
  python objects/dse-fix-opt/eval/run_harness.py --repo-root . \
    --deterministic --write-evidence
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from graders import grade_all


OBJECT_NAME = "dse-fix-opt"
OBJECT_VERSION = "v1.1.0"


def _utc_now_iso(deterministic: bool) -> str:
    if deterministic:
        # Fixed timestamp to make reference evidence reproducible and diff-stable.
        return "1970-01-01T00:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


def run_case(repo_root: Path, case_path: Path) -> dict:
    try:
        spec = json.loads(case_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "case": case_path.name,
            "passed": False,
            "error": f"Case JSON parse failure: {e!r}",
        }

    bundle_rel = spec.get("bundle_path")
    if not bundle_rel:
        return {
            "case": spec.get("id", case_path.name),
            "passed": False,
            "error": "bundle_path missing",
        }

    bundle_path = repo_root / bundle_rel
    if not bundle_path.exists():
        return {
            "case": spec.get("id", case_path.name),
            "passed": False,
            "error": f"Bundle path not found: {bundle_rel}",
        }

    text = bundle_path.read_text(encoding="utf-8")
    exp = spec.get("expect", {})
    try:
        results = grade_all(
            text=text,
            required_sections=exp["required_sections"],
            eval_gates=exp["required_gates"]["eval"],
            release_gates=exp["required_gates"]["release"],
            min_max_tokens=int(exp["min_max_tokens"]),
        )
    except Exception as e:
        return {
            "case": spec.get("id", case_path.name),
            "passed": False,
            "error": f"Grader execution failure: {e!r}",
        }

    passed = all(r.passed for r in results)
    gates_total = len(results)
    gates_passed = sum(1 for r in results if r.passed)
    # Binary score: 100 iff all gates pass, else 0. This matches "≥98" as "all PASS".
    score = 100 if passed else 0

    return {
        "case": spec.get("id", case_path.name),
        "description": spec.get("description", ""),
        "bundle_path": bundle_rel,
        "passed": passed,
        "score": score,
        "gates_total": gates_total,
        "gates_passed": gates_passed,
        "grades": [asdict(r) for r in results],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repository root (default: .)")
    ap.add_argument(
        "--cases", default=f"objects/{OBJECT_NAME}/eval/cases", help="Cases directory"
    )
    ap.add_argument(
        "--write-evidence",
        action="store_true",
        help="Write report under artifacts/evidence/",
    )
    ap.add_argument(
        "--deterministic",
        action="store_true",
        help="Freeze timestamp and write to artifacts/evidence/reference/ for commit-stable evidence",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    cases_dir = (repo_root / args.cases).resolve()

    case_files = sorted([p for p in cases_dir.glob("*.json") if p.is_file()])
    if not case_files:
        print(json.dumps({"passed": False, "error": f"No cases found in {cases_dir}"}))
        return 2

    report = {
        "object": OBJECT_NAME,
        "version": OBJECT_VERSION,
        "timestamp_utc": _utc_now_iso(args.deterministic),
        "cases": [],
    }

    for cp in case_files:
        report["cases"].append(run_case(repo_root, cp))

    report["passed"] = all(c.get("passed") for c in report["cases"])
    report["score"] = 100 if report["passed"] else 0

    out = json.dumps(report, indent=2, sort_keys=False)
    print(out)

    if args.write_evidence:
        ev_root = repo_root / f"objects/{OBJECT_NAME}/artifacts/evidence"
        run_id = (
            "reference"
            if args.deterministic
            else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
        out_dir = ev_root / run_id / "eval"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(out + "\n", encoding="utf-8")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
