#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

USES_RE = re.compile(r"^[^@\s]+@([^\s]+)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    args = p.parse_args()

    violations: list[str] = []
    for wf in sorted(args.workflows.glob("*.yml")):
        data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            for idx, step in enumerate(job.get("steps", [])):
                if not isinstance(step, dict) or not isinstance(step.get("uses"), str):
                    continue
                uses = step["uses"]
                ref_match = USES_RE.match(uses)
                if not ref_match:
                    continue
                action = uses.split("@", 1)[0]
                ref = ref_match.group(1)
                if action.startswith("./"):
                    continue
                if not SHA_RE.match(ref):
                    violations.append(f"{wf.name}:{job_name}:step_{idx}:{uses}")
    if violations:
        print(
            "FAIL: unpinned actions detected (all non-local actions must be full SHA)"
        )
        for v in violations:
            print(v)
        return 1
    print("PASS: action pinning policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
