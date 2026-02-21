from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml


def _normalize_inline_command(line: str) -> str:
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return ""
    if "python -c " in cleaned or "node -e " in cleaned:
        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        return f"inline-script sha256:{digest}"
    return cleaned


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
                if not (isinstance(step, dict) and isinstance(step.get("run"), str)):
                    continue
                heredoc_end: str | None = None
                for raw in step["run"].splitlines():
                    line = raw.strip()
                    if heredoc_end is not None:
                        if line == heredoc_end:
                            commands.append(
                                f"heredoc-body sha256:<normalized:{heredoc_end}>"
                            )
                            heredoc_end = None
                        continue
                    match = re.search(r"<<[-~]?['\"]?([A-Za-z0-9_]+)['\"]?", line)
                    if match:
                        heredoc_end = match.group(1)
                        commands.append(_normalize_inline_command(raw))
                        continue
                    normalized = _normalize_inline_command(raw)
                    if normalized:
                        commands.append(normalized)
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
            "install": [
                "python -m pip install -r requirements.lock",
                "python -m pip install -r requirements-dev.txt",
            ],
            "tests": ["python -m pytest -q -W error"],
            "lint_format": ["ruff check .", "ruff format --check ."],
            "typecheck": ["mypy ."],
            "validate": [
                "python scripts/validate_arsenal.py --repo-root . --strict",
                "python scripts/run_object_evals.py --repo-root .",
                "python tools/verify_protocol_consistency.py --protocol protocol.yaml",
                "python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json",
                "python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json",
                "python tools/generate_titan9_proof.py --repo-root .",
            ],
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
