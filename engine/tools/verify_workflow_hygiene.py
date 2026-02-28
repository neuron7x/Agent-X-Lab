#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _iter_workflows(root: Path) -> list[Path]:
    return sorted(
        set(root.rglob("*.yml")).union(root.rglob("*.yaml")),
        key=lambda p: p.relative_to(root).as_posix(),
    )


def _merged_env(*env_maps: object) -> dict[str, str]:
    merged: dict[str, str] = {}
    for env_map in env_maps:
        if isinstance(env_map, dict):
            for k, v in env_map.items():
                merged[str(k)] = str(v)
    return merged




def _resolve_workflows_root(requested: Path) -> Path | None:
    resolved = requested.resolve()
    if resolved.exists() and resolved.is_dir():
        return resolved

    if requested == Path(".github/workflows"):
        here = Path.cwd().resolve()
        for candidate in [here, *here.parents]:
            wf = candidate / ".github" / "workflows"
            if wf.exists() and wf.is_dir():
                return wf.resolve()

    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    args = parser.parse_args()

    root = _resolve_workflows_root(args.workflows)
    if root is None:
        print(f"FAIL: workflows directory not found: {args.workflows}")
        return 2

    workflows = _iter_workflows(root)
    if not workflows:
        print(f"FAIL: no workflow files found under: {args.workflows}")
        return 2

    errs: list[str] = []
    parse_errors: list[str] = []

    for wf in workflows:
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
            errs.append(f"{rel}:invalid_yaml_document")
            continue

        if not isinstance(data.get("permissions"), dict):
            errs.append(f"{rel}:missing_permissions")
        if not isinstance(data.get("concurrency"), dict):
            errs.append(f"{rel}:missing_concurrency")

        root_env = data.get("env") if isinstance(data.get("env"), dict) else {}
        jobs = data.get("jobs", {}) if isinstance(data.get("jobs"), dict) else {}
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            if "timeout-minutes" not in job:
                errs.append(f"{rel}:{job_name}:missing_timeout")
            job_env = job.get("env") if isinstance(job.get("env"), dict) else {}
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if uses == "./.github/actions/pin-pip":
                    step_env = step.get("env") if isinstance(step.get("env"), dict) else {}
                    merged = _merged_env(root_env, job_env, step_env)
                    if not merged.get("PIP_VERSION"):
                        errs.append(
                            f"{rel}:{job_name}:step_{idx}:missing_pip_version_for_pin_pip"
                        )

    if parse_errors:
        print("FAIL: invalid workflow YAML detected")
        for item in parse_errors:
            print(item)
        return 2

    if errs:
        print("FAIL: workflow hygiene violations")
        print("\n".join(errs))
        return 1

    print("PASS: workflow hygiene policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
