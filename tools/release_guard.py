#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
RELEASE_NOTES = REPO_ROOT / "docs" / "release-notes.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _project_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _has_heading(content: str, heading: str) -> bool:
    return f"\n## {heading}\n" in f"\n{content}"


def _has_changelog_version(content: str, version: str) -> bool:
    return bool(re.search(rf"^## \[{re.escape(version)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?$", content, flags=re.MULTILINE))


def _check_release_docs(version: str, errors: list[str]) -> None:
    if not CHANGELOG.exists() or not RELEASE_NOTES.exists():
        return

    changelog = CHANGELOG.read_text(encoding="utf-8")
    notes = RELEASE_NOTES.read_text(encoding="utf-8")

    _require(
        _has_changelog_version(changelog, version),
        f"CHANGELOG.md missing version section for {version}",
        errors,
    )
    _require(
        _has_heading(notes, version),
        f"docs/release-notes.md missing version section for {version}",
        errors,
    )


def _changed_files(base_ref: str | None) -> set[str]:
    if base_ref:
        try:
            _run_git("fetch", "--depth", "1", "origin", base_ref)
        except subprocess.CalledProcessError:
            pass
    merge_base = (
        _run_git("merge-base", "HEAD", f"origin/{base_ref}")
        if base_ref
        else _run_git("rev-parse", "HEAD~1")
    )
    output = _run_git("diff", "--name-only", f"{merge_base}...HEAD")
    return {line for line in output.splitlines() if line}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pr", "release"], required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--base-ref", default="")
    args = parser.parse_args()

    errors: list[str] = []
    version = args.version or _project_version()

    _require(PYPROJECT.exists(), "missing pyproject.toml", errors)
    _require(CHANGELOG.exists(), "missing CHANGELOG.md", errors)
    _require(RELEASE_NOTES.exists(), "missing docs/release-notes.md", errors)

    if args.mode == "release":
        _check_release_docs(version, errors)
    else:
        if CHANGELOG.exists() and RELEASE_NOTES.exists():
            changelog_text = CHANGELOG.read_text(encoding="utf-8")
            notes_text = RELEASE_NOTES.read_text(encoding="utf-8")
            _require(_has_heading(changelog_text, "[Unreleased]"), "CHANGELOG.md missing [Unreleased]", errors)
            _require(_has_heading(notes_text, "Unreleased"), "docs/release-notes.md missing Unreleased", errors)

        changed = _changed_files(args.base_ref or None)
        if "pyproject.toml" in changed:
            _require(
                "CHANGELOG.md" in changed,
                "pyproject.toml changed but CHANGELOG.md not updated",
                errors,
            )
            _require(
                "docs/release-notes.md" in changed,
                "pyproject.toml changed but docs/release-notes.md not updated",
                errors,
            )

    if errors:
        print("FAIL: release guard")
        for err in sorted(errors):
            print(f"- {err}")
        return 1

    print("PASS: release guard")
    print(f"version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
