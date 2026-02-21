#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    args = p.parse_args()

    errs: list[str] = []
    for wf in sorted(args.workflows.glob("*.yml")):
        data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            errs.append(f"{wf.name}:invalid_yaml")
            continue
        if not isinstance(data.get("permissions"), dict):
            errs.append(f"{wf.name}:missing_permissions")
        if not isinstance(data.get("concurrency"), dict):
            errs.append(f"{wf.name}:missing_concurrency")
        jobs = data.get("jobs", {}) if isinstance(data.get("jobs"), dict) else {}
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            if "timeout-minutes" not in job:
                errs.append(f"{wf.name}:{job_name}:missing_timeout")
    if errs:
        print("FAIL: workflow hygiene violations")
        print("\n".join(errs))
        return 1
    print("PASS: workflow hygiene policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
