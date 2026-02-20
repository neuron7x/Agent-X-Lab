from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

QUICKSTART_HEADER = "## Quickstart"
SEED_REQUIREMENT = "PYTHONHASHSEED=0"
REQUIRED_QUICKSTART_COMMANDS = ["make setup", "make test", "make proof"]
E_README_CONTRACT_VIOLATION = "E_README_CONTRACT_VIOLATION: README Quickstart must require PYTHONHASHSEED=0 and run exactly 'make setup', 'make test', 'make proof'."


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
        if (
            in_quickstart
            and (line.startswith("## ") or line.startswith("### "))
            and line != QUICKSTART_HEADER
        ):
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


def _validate_quickstart_contract(
    readme_text: str, quickstart_commands: list[str]
) -> None:
    if SEED_REQUIREMENT not in readme_text:
        raise SystemExit(E_README_CONTRACT_VIOLATION)
    if quickstart_commands != REQUIRED_QUICKSTART_COMMANDS:
        raise SystemExit(E_README_CONTRACT_VIOLATION)


def _parse_workflows(workflows_dir: Path) -> tuple[set[str], list[str]]:
    workflow_commands: set[str] = set()
    seed_violations: list[str] = []
    for workflow_file in sorted(workflows_dir.glob("*.yml")):
        data = yaml.safe_load(workflow_file.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        root_env = data.get("env", {}) if isinstance(data.get("env"), dict) else {}
        jobs = data.get("jobs", {}) if isinstance(data.get("jobs"), dict) else {}
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            job_env = dict(root_env)
            if isinstance(job.get("env"), dict):
                job_env.update(job["env"])
            for index, step in enumerate(job.get("steps", [])):
                if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                    continue
                step_env = dict(job_env)
                if isinstance(step.get("env"), dict):
                    step_env.update(step["env"])
                if str(step_env.get("PYTHONHASHSEED", "")) != "0":
                    step_name = step.get("name") or f"step_{index}"
                    seed_violations.append(
                        f"{workflow_file.name}:{job_name}:{step_name}"
                    )
                for line in step["run"].splitlines():
                    cmd = line.strip()
                    if cmd and not cmd.startswith("#"):
                        workflow_commands.add(cmd)
    return workflow_commands, seed_violations


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
    _validate_quickstart_contract(readme_text, quickstart_commands)

    workflow_commands, seed_violations = _parse_workflows(args.workflows)
    if seed_violations:
        raise SystemExit(
            "PYTHONHASHSEED=0 must be set for tooling steps in "
            + ", ".join(seed_violations)
        )
    if "make ci" not in workflow_commands:
        raise SystemExit("E_README_CONTRACT_VIOLATION: workflows must run make ci.")

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
