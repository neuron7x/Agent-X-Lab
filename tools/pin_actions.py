#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PIN_MAP = {
    "actions/checkout@v4": "actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4",
    "actions/setup-python@v5": "actions/setup-python@82c7e631bb3cdc910f68e0081d67478d79c6982d # v5",
    "actions/upload-artifact@v4": "actions/upload-artifact@65462800fd760344b1a7b4382951275a0abb4808 # v4",
    "actions/github-script@v7": "actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea # v7",
    "actions/dependency-review-action@v4": "actions/dependency-review-action@0c155d3d7a5fd09c8e5e9f44d3f10f5f4f2f0fcb # v4",
    "github/codeql-action/init@v3": "github/codeql-action/init@b8f6507f3f5d3b9332f3d3e6585f6f8eecc65c0a # v3",
    "github/codeql-action/analyze@v3": "github/codeql-action/analyze@b8f6507f3f5d3b9332f3d3e6585f6f8eecc65c0a # v3",
    "github/codeql-action/upload-sarif@v3": "github/codeql-action/upload-sarif@b8f6507f3f5d3b9332f3d3e6585f6f8eecc65c0a # v3",
    "ossf/scorecard-action@v2.3.1": "ossf/scorecard-action@62b7fcb92755d80d6e46e3f6d2f13213dcd89f05 # v2.3.1",
    "gitleaks/gitleaks-action@v2": "gitleaks/gitleaks-action@5f01c89e30d8f6f99de11e2f38f58d1826e02f8a # v2",
    "reviewdog/action-actionlint@v1": "reviewdog/action-actionlint@c4f5a5f15cd9f6d9639efefab9f06b9a3170f12e # v1",
}

USES_RE = re.compile(r"(?m)^(\s*-\s*uses:\s*)([^\s#]+)\s*$")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    args = p.parse_args()

    for wf in sorted(args.workflows.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")

        def repl(m: re.Match[str]) -> str:
            prefix, uses = m.group(1), m.group(2)
            return f"{prefix}{PIN_MAP.get(uses, uses)}"

        wf.write_text(USES_RE.sub(repl, text), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
