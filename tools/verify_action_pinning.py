#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

import yaml

USES_RE = re.compile(r"^[^@\s]+@([^\s]+)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_allowlist(path: Path) -> dict[str, date]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("allow", [])
    out: dict[str, date] = {}
    for item in items:
        action = str(item.get("action", "")).strip()
        expires = datetime.strptime(str(item.get("expires", "")), "%Y-%m-%d").date()
        if action:
            out[action] = expires
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    p.add_argument(
        "--allowlist", type=Path, default=Path("policies/action_pinning_allowlist.json")
    )
    args = p.parse_args()

    today = date.today()
    allowlist = load_allowlist(args.allowlist)
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
                if (
                    action.startswith("actions/")
                    or action.startswith("github/")
                    or action.startswith("./")
                ):
                    continue
                if SHA_RE.match(ref):
                    continue
                if action in allowlist and allowlist[action] >= today:
                    continue
                violations.append(f"{wf.name}:{job_name}:step_{idx}:{uses}")
    if violations:
        print("FAIL: unpinned third-party actions detected")
        for v in violations:
            print(v)
        return 1
    print("PASS: action pinning policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
