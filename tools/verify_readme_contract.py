from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

QUICKSTART_HEADER = "## Quickstart"


def _extract_quickstart_commands(readme_text: str) -> list[str]:
    count = readme_text.count(QUICKSTART_HEADER)
    if count != 1:
        raise ValueError(
            f"README must contain exactly one '{QUICKSTART_HEADER}' section; found {count}"
        )

    lines = readme_text.splitlines()
    commands: list[str] = []
    in_quickstart = False
    in_code = False
    for line in lines:
        if line.startswith("## ") and line != QUICKSTART_HEADER:
            if in_quickstart:
                break
        if line == QUICKSTART_HEADER:
            in_quickstart = True
            continue
        if not in_quickstart:
            continue
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            cmd = line.strip()
            if cmd:
                commands.append(cmd)
    if not commands:
        raise ValueError("No commands found in README Quickstart code blocks")
    return commands


def _parse_workflow_commands(workflows_dir: Path) -> set[str]:
    workflow_commands: set[str] = set()
    for workflow_file in sorted(workflows_dir.glob("*.yml")):
        data = yaml.safe_load(workflow_file.read_text(encoding="utf-8")) or {}
        jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
        for job in jobs.values() if isinstance(jobs, dict) else []:
            if not isinstance(job, dict):
                continue
            for step in job.get("steps", []):
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    for line in step["run"].splitlines():
                        cmd = line.strip()
                        if cmd and not cmd.startswith("#"):
                            workflow_commands.add(cmd)
    return workflow_commands


def _validate_readme_links(repo_root: Path, readme_text: str) -> list[str]:
    missing: list[str] = []
    for target in re.findall(r"\[[^\]]+\]\((docs/[^)]+|scripts/[^)]+)\)", readme_text):
        if not (repo_root / target).exists():
            missing.append(target)
    return sorted(set(missing))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--workflows", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path.cwd()
    readme_text = args.readme.read_text(encoding="utf-8")
    quickstart_commands = _extract_quickstart_commands(readme_text)
    workflow_commands = _parse_workflow_commands(args.workflows)

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    canonical = inventory.get("canonical_commands", {})
    canonical_flat = {
        cmd
        for values in canonical.values()
        for cmd in (values if isinstance(values, list) else [])
        if isinstance(cmd, str)
    }

    missing_in_ci = sorted(
        cmd
        for cmd in quickstart_commands
        if cmd not in workflow_commands and cmd not in canonical_flat
    )
    if missing_in_ci:
        raise SystemExit(
            "README commands are not represented in workflow/inventory canonical set: "
            + ", ".join(missing_in_ci)
        )

    missing_links = _validate_readme_links(repo_root, readme_text)
    if missing_links:
        raise SystemExit("README references missing paths: " + ", ".join(missing_links))

    out_dir = Path("artifacts/titan9")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "readme_commands.json").write_text(
        json.dumps(
            {"quickstart_commands": quickstart_commands}, indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
