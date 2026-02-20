from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def verify(protocol_path: Path) -> dict[str, object]:
    data = yaml.safe_load(protocol_path.read_text(encoding="utf-8")) or {}
    deficits = data.get("deficits", [])
    steps = data.get("protocol_plan", [])

    deficit_ids = [
        item["id"]
        for item in deficits
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    step_fixes: dict[str, list[str]] = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = step.get("step_id")
        fixes = step.get("fixes", [])
        if isinstance(step_id, str):
            step_fixes[step_id] = [f for f in fixes if isinstance(f, str)]

    seen: dict[str, int] = {}
    for fixes in step_fixes.values():
        for deficit in fixes:
            seen[deficit] = seen.get(deficit, 0) + 1

    missing_deficits = sorted(d for d in deficit_ids if d not in seen)
    duplicate_deficits = sorted(d for d, count in seen.items() if count > 1)
    orphan_steps = sorted(step_id for step_id, fixes in step_fixes.items() if not fixes)
    unknown_deficits = sorted(d for d in seen if d not in set(deficit_ids))

    passed = not (
        missing_deficits or duplicate_deficits or orphan_steps or unknown_deficits
    )
    return {
        "pass": passed,
        "missing_deficits": missing_deficits,
        "duplicate_deficits": duplicate_deficits,
        "orphan_steps": orphan_steps,
        "unknown_deficits": unknown_deficits,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()

    result = verify(args.protocol)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
