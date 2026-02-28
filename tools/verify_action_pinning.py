#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

USES_RE = re.compile(r"^\s*-\s*uses:\s*['\"]?([^'\"\s]+)['\"]?\s*$")
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def _iter_workflows(root: Path) -> list[Path]:
    return sorted([*root.rglob("*.yml"), *root.rglob("*.yaml")])


def _is_allowed(action_ref: str) -> bool:
    if action_ref.startswith("./") or action_ref.startswith("docker://"):
        return True
    return bool(PIN_RE.match(action_ref))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    args = ap.parse_args()

    workflows_root = args.workflows.resolve()
    failures: list[str] = []

    for wf in _iter_workflows(workflows_root):
        rel = wf.relative_to(workflows_root).as_posix()
        for idx, line in enumerate(wf.read_text(encoding="utf-8", errors="replace").splitlines()):
            m = USES_RE.match(line)
            if not m:
                continue
            action_ref = m.group(1)
            if not _is_allowed(action_ref):
                failures.append(f"{rel}:line_{idx + 1}:{action_ref}")

    if failures:
        print("FAIL: unpinned action references detected")
        for item in failures:
            print(item)
        return 1

    print("OK: all workflow actions are SHA-pinned (or local/docker references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
