#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _merged_env(*env_maps: object) -> dict[str, str]:
    merged: dict[str, str] = {}
    for env_map in env_maps:
        if isinstance(env_map, dict):
            for k, v in env_map.items():
                merged[str(k)] = str(v)
    return merged


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path)
    args = p.parse_args()

    if args.workflows is None:
        workflows_dir = None
        for candidate in (Path.cwd(), *Path.cwd().parents):
            discovered = candidate / ".github" / "workflows"
            if discovered.is_dir():
                workflows_dir = discovered
                break
        if workflows_dir is None:
            print("FAIL: workflow hygiene validation setup failed")
            print("workflows directory not found; pass --workflows or run within a repository containing .github/workflows")
            return 2
    else:
        workflows_dir = args.workflows.resolve()

    if not workflows_dir.exists():
        print("FAIL: workflow hygiene validation setup failed")
        print(f"workflows directory does not exist: {workflows_dir}")
        return 2
    if not workflows_dir.is_dir():
        print("FAIL: workflow hygiene validation setup failed")
        print(f"workflows path is not a directory: {workflows_dir}")
        return 2

    workflow_files = sorted(set(workflows_dir.glob("*.yml")).union(workflows_dir.glob("*.yaml")))
    if not workflow_files:
        print("FAIL: workflow hygiene validation setup failed")
        print(f"no workflow files found in: {workflows_dir}")
        return 2

    errs: list[str] = []
    parse_errors: list[str] = []
    for wf in workflow_files:
        try:
            data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            parse_errors.append(f"{wf.name}: {exc}")
            continue
        except OSError as exc:
            parse_errors.append(f"{wf.name}: {exc}")
            continue
        if not isinstance(data, dict):
            errs.append(f"{wf.name}:invalid_yaml")
            continue
        if not isinstance(data.get("permissions"), dict):
            errs.append(f"{wf.name}:missing_permissions")
        if not isinstance(data.get("concurrency"), dict):
            errs.append(f"{wf.name}:missing_concurrency")
        root_env = data.get("env") if isinstance(data.get("env"), dict) else {}
        jobs = data.get("jobs", {}) if isinstance(data.get("jobs"), dict) else {}
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            if "timeout-minutes" not in job:
                errs.append(f"{wf.name}:{job_name}:missing_timeout")
            job_env = job.get("env") if isinstance(job.get("env"), dict) else {}
            for idx, step in enumerate(job.get("steps", [])):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if uses == "./.github/actions/pin-pip":
                    step_env = (
                        step.get("env") if isinstance(step.get("env"), dict) else {}
                    )
                    merged = _merged_env(root_env, job_env, step_env)
                    if not merged.get("PIP_VERSION"):
                        errs.append(
                            f"{wf.name}:{job_name}:step_{idx}:missing_pip_version_for_pin_pip"
                        )
    if parse_errors:
        print("FAIL: invalid workflow YAML detected")
        print("\n".join(parse_errors))
        return 2

    if errs:
        print("FAIL: workflow hygiene violations")
        print("\n".join(errs))
        return 1
    print("PASS: workflow hygiene policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
