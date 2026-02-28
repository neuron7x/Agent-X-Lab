#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _discover_default_workflows_dir() -> Path | None:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        workflows = candidate / ".github" / "workflows"
        if workflows.is_dir():
            return workflows
    return None


def _resolve_workflow_dir(workflows_arg: Path | None) -> tuple[Path | None, list[str]]:
    if workflows_arg is None:
        root = _discover_default_workflows_dir()
        if root is None:
            return None, [
                "workflows directory not found; pass --workflows or run within a repository containing .github/workflows"
            ]
    else:
        root = workflows_arg.resolve()

    if not root.exists():
        return None, [f"workflows directory does not exist: {root}"]
    if not root.is_dir():
        return None, [f"workflows path is not a directory: {root}"]

    workflows = _iter_workflows(root)
    if not workflows:
        return None, [f"no workflow files found in: {root}"]
    return root, []


def _iter_workflows(root: Path) -> list[Path]:
    return sorted(
        set(root.rglob("*.yml")).union(root.rglob("*.yaml")),
        key=lambda p: p.relative_to(root).as_posix(),
    )


def _is_allowed_ref(uses: str) -> bool:
    if uses.startswith("./") or uses.startswith("docker://"):
        return True
    if "@" not in uses:
        return False
    _, ref = uses.rsplit("@", 1)
    return bool(SHA_RE.fullmatch(ref))


def _collect_uses_entries(doc: dict[str, Any]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    jobs = doc.get("jobs", {})
    if not isinstance(jobs, dict):
        return entries

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue

        job_uses = job.get("uses")
        if isinstance(job_uses, str):
            entries.append((f"{job_name}:uses", job_uses))

        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_uses = step.get("uses")
            if isinstance(step_uses, str):
                entries.append((f"{job_name}:step_{idx}", step_uses))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", type=Path)
    args = parser.parse_args()

    root, setup_errors = _resolve_workflow_dir(args.workflows)
    if setup_errors:
        print("FAIL: workflows directory validation failed")
        for item in setup_errors:
            print(item)
        return 2
    assert root is not None

    violations: list[str] = []
    parse_errors: list[str] = []

    for wf in _iter_workflows(root):
        rel = wf.relative_to(root).as_posix()
        try:
            data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            parse_errors.append(f"{rel}: {exc}")
            continue
        except OSError as exc:
            parse_errors.append(f"{rel}: {exc}")
            continue

        if not isinstance(data, dict):
            continue

        for context, uses in _collect_uses_entries(data):
            if not _is_allowed_ref(uses):
                violations.append(f"{rel}:{context}:{uses}")

    if parse_errors:
        print("FAIL: invalid workflow YAML detected")
        for item in parse_errors:
            print(item)
        return 2

    if violations:
        print("FAIL: unpinned action references detected")
        for item in violations:
            print(item)
        return 1

    print("OK: all workflow actions are SHA-pinned (or local/docker references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
