#!/usr/bin/env python3
"""Generate a CSI-style proof bundle for deterministic local validation."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CommandSpec:
    log_name: str
    command: list[str]


def run_and_log(repo_root: Path, proof_dir: Path, spec: CommandSpec) -> int:
    """Run a command from repo root and write a structured log file."""
    result = subprocess.run(
        spec.command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    lines = [
        f"command: {' '.join(spec.command)}",
        f"exit_code: {result.returncode}",
        "stdout:",
        result.stdout.rstrip() or "<empty>",
        "stderr:",
        result.stderr.rstrip() or "<empty>",
        "",
    ]
    (proof_dir / spec.log_name).write_text("\n".join(lines), encoding="utf-8")
    return result.returncode


def write_change_summary(proof_dir: Path) -> None:
    summary = (
        "# Change Summary\n\n"
        "- Added a deterministic proof bundle generator script.\n"
        "- Added tests validating structured proof log output.\n"
    )
    (proof_dir / "change_summary.md").write_text(summary, encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--proof-dir",
        default="proof",
        help="Output directory for proof bundle files",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path(args.repo_root).resolve()
    proof_dir = (repo_root / args.proof_dir).resolve()
    proof_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        CommandSpec("tool_versions.txt", ["python", "--version"]),
        CommandSpec("reproduction.log", ["python", "-m", "pytest", "-q"]),
        CommandSpec("fix_validation.log", ["ruff", "check", "."]),
        CommandSpec("test_results.log", ["make", "test"]),
    ]

    exit_codes = [run_and_log(repo_root, proof_dir, spec) for spec in specs]
    write_change_summary(proof_dir)

    return 0 if all(code == 0 for code in exit_codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
