from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CRITICAL_START = "CRITICAL_START"
CRITICAL_END = "CRITICAL_END"
ID_RE = re.compile(r"\b(agent_id|gate_id|step_id)\s*[:=]\s*['\"]?([A-Za-z0-9_-]+)")
LOWER_UNDERSCORE_RE = re.compile(r"^[a-z0-9_]+$")
MAX_MIDDLE_BLOCK_LINES = 400


def _collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            files.append(p)
            continue
        if p.exists() and p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json"}:
                    files.append(child)
    return files


def lint_file(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if CRITICAL_START in text and CRITICAL_END not in text:
        issues.append("E_CRITICAL_END_MISSING")
    if CRITICAL_END in text and CRITICAL_START not in text:
        issues.append("E_CRITICAL_START_MISSING")


    if CRITICAL_START in text and CRITICAL_END in text:
        start_idx = next(i for i, line in enumerate(lines) if CRITICAL_START in line)
        end_idx = next(i for i, line in enumerate(lines) if CRITICAL_END in line)
        if end_idx > start_idx and (end_idx - start_idx) > MAX_MIDDLE_BLOCK_LINES:
            issues.append("E_MIDDLE_BLOCK_OVERSIZED")

    for idx, line in enumerate(lines, start=1):
        match = ID_RE.search(line)
        if not match:
            continue
        value = match.group(2)
        if not LOWER_UNDERSCORE_RE.match(value):
            issues.append(f"E_ID_POLICY:{idx}:{match.group(1)}={value}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths", nargs="+", required=True)
    args = parser.parse_args()

    files = _collect_files(args.paths)
    report: dict[str, list[str]] = {}
    for path in files:
        issues = lint_file(path)
        if issues:
            report[str(path)] = issues

    out_dir = Path("artifacts/proof/lint")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prompt_lint_report.json"
    out_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    if report:
        print(json.dumps(report, sort_keys=True))
        raise SystemExit(1)
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
