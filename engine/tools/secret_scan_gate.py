#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]


def _all_files_fallback(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root)
        if any(
            part
            in {
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                ".ruff_cache",
                ".mypy_cache",
            }
            for part in rel.parts
        ):
            continue
        files.append(path)
    return files


def _tracked_files(repo_root: Path) -> list[Path]:
    p = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=False
    )
    if p.returncode != 0:
        return _all_files_fallback(repo_root)
    return [repo_root / line for line in p.stdout.splitlines() if line.strip()]


def _resolve_output_path(repo_root: Path, out: Path) -> Path:
    candidate = out if out.is_absolute() else (repo_root / out)
    resolved = candidate.resolve()
    artifact_root = (repo_root / "artifacts").resolve()
    try:
        resolved.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError(
            f"output path must be under artifacts/: {resolved}"
        ) from exc
    return resolved

def _scan_file(path: Path, repo_root: Path) -> list[dict[str, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    findings: list[dict[str, object]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(
                    {
                        "rule": name,
                        "path": str(path.relative_to(repo_root)),
                        "line": idx,
                        "excerpt": line[:200],
                    }
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--out", type=Path, default=Path("artifacts/security/secret-scan.json")
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    all_findings: list[dict[str, object]] = []
    for file_path in _tracked_files(repo_root):
        rel = str(file_path.relative_to(repo_root))
        if rel.startswith("tests/") or rel.startswith("artifacts/"):
            continue
        all_findings.extend(_scan_file(file_path, repo_root))

    try:
        out_path = _resolve_output_path(repo_root, args.out)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 2

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not all_findings else "fail",
        "findings": all_findings,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if all_findings:
        print("FAIL: potential secrets detected")
        for f in all_findings:
            print(f"{f['path']}:{f['line']}:{f['rule']}")
        return 1
    print("PASS: no hardcoded secrets detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
