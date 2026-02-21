from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


def _parse_workflow_commands(workflows_dir: Path) -> list[str]:
    commands: list[str] = []
    for workflow_file in sorted(workflows_dir.glob("*.yml")):
        workflow = yaml.safe_load(workflow_file.read_text(encoding="utf-8")) or {}
        jobs = workflow.get("jobs", {})
        if not isinstance(jobs, dict):
            continue
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps", []):
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    for line in step["run"].splitlines():
                        cleaned = line.strip()
                        if cleaned and not cleaned.startswith("#"):
                            commands.append(cleaned)
    return sorted(set(commands))


def build_inventory(repo_root: Path) -> dict[str, object]:
    pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    requires_python_match = re.search(
        r'^requires-python\s*=\s*"([^"]+)"', pyproject_text, flags=re.MULTILINE
    )
    scripts = sorted(
        re.findall(
            r'^([a-zA-Z0-9_-]+)\s*=\s*"exoneural_governor\.cli:main"',
            pyproject_text,
            flags=re.MULTILINE,
        )
    )

    return {
        "python_requires": requires_python_match.group(1)
        if requires_python_match
        else None,
        "tooling": ["ruff", "mypy", "pytest"],
        "entrypoints": scripts,
        "demo_artifacts": ["VR.json", "artifacts/release/*.zip"],
        "canonical_commands": {
            "setup": ["make setup"],
            "tests": ["make test"],
            "proof": ["make proof"],
            "ci": ["make ci"],
        },
        "workflows": {
            "commands": _parse_workflow_commands(repo_root / ".github" / "workflows")
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    inventory = build_inventory(args.repo_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
