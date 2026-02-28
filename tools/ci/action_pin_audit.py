#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([\w.-]+/[\w.-]+)@([^\s#]+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()

    violations = []
    checked = []
    for path in sorted(pathlib.Path(".github/workflows").glob("*.yml")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES_RE.match(line)
            if not match:
                continue
            action, ref = match.groups()
            checked.append(f"{path}:{line_no}:{action}@{ref}")
            if not SHA_RE.fullmatch(ref):
                violations.append(f"{path}:{line_no}:{action}@{ref}")

    print(f"CHECKED={len(checked)}")
    for row in checked:
        print(f"OK {row}")
    print(f"VIOLATIONS={len(violations)}")
    for row in violations:
        print(f"VIOLATION {row}")

    if args.fail and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
