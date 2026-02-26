#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

THRESHOLD_BYTES = 5 * 1024 * 1024


def run_git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line for line in result.stdout.splitlines() if line]
    files.sort()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="", help="Path to write JSON output")
    args = parser.parse_args()

    findings = []
    for path in run_git_ls_files():
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        if size > THRESHOLD_BYTES:
            findings.append({"path": path, "size_bytes": size})

    findings.sort(key=lambda item: (-item["size_bytes"], item["path"]))
    top20 = findings[:20]

    print("# Large tracked files (>5MB), top 20")
    if not top20:
        print("none")
    else:
        for item in top20:
            print(f"{item['size_bytes']}\t{item['path']}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(top20, f, indent=2, sort_keys=True)
            f.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
