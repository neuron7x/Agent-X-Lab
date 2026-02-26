#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+-]+$")


def _is_requirement_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped and not stripped.startswith("#"))


def _check_file(path: Path) -> list[str]:
    issues: list[str] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not _is_requirement_line(raw):
            continue
        line = raw.strip()
        if "@" in line or "git+" in line or "http://" in line or "https://" in line:
            issues.append(f"{path}:{idx}:non-hermetic source is forbidden: {line}")
            continue
        if not PIN_RE.match(line):
            issues.append(
                f"{path}:{idx}:dependency must be strictly pinned with == : {line}"
            )
    return issues


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--requirements", action="append", required=True)
    p.add_argument(
        "--out", type=Path, default=Path("artifacts/security/dependency-review.json")
    )
    args = p.parse_args()

    issues: list[str] = []
    for req in args.requirements:
        path = Path(req)
        if not path.exists():
            issues.append(f"{path}:missing")
            continue
        issues.extend(_check_file(path))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "requirements": args.requirements,
    }
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if issues:
        print("FAIL: dependency review policy violations")
        for issue in issues:
            print(issue)
        return 1
    print("PASS: dependency review policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
