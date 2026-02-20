#!/usr/bin/env python3
"""
Run eval harnesses for all objects declared in root MANIFEST.json.

Fail-closed:
  - missing harness / non-zero exit / non-JSON output => FAIL

Usage:
  python scripts/run_object_evals.py --repo-root . --write-evidence
  python scripts/run_object_evals.py --repo-root . --deterministic --write-evidence
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_harness(
    repo_root: Path, harness: Path, write_evidence: bool, deterministic: bool
) -> Dict[str, Any]:
    cmd = ["python", str(harness), "--repo-root", str(repo_root)]
    if deterministic:
        cmd.append("--deterministic")
    if write_evidence:
        cmd.append("--write-evidence")

    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()

    if p.returncode != 0:
        return {
            "passed": False,
            "returncode": p.returncode,
            "error": "harness exited non-zero",
            "stderr": err[:4000],
            "stdout": out[:4000],
        }

    try:
        j = json.loads(out)
    except Exception as e:
        return {
            "passed": False,
            "returncode": p.returncode,
            "error": f"harness output is not JSON: {e!r}",
            "stderr": err[:4000],
            "stdout": out[:4000],
        }

    return {
        "passed": bool(j.get("passed")),
        "score": int(j.get("score", 0)),
        "report": j,
        "stderr": err[:4000],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--manifest",
        default="MANIFEST.json",
        help="Root manifest (default: MANIFEST.json)",
    )
    ap.add_argument(
        "--write-evidence",
        action="store_true",
        help="Forward --write-evidence to harnesses",
    )
    ap.add_argument(
        "--deterministic",
        action="store_true",
        help="Forward --deterministic to harnesses",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    m = load_json(repo_root / args.manifest)

    results: List[Dict[str, Any]] = []
    passed_all = True

    for obj in m.get("objects", []):
        name = (obj or {}).get("name")
        if not name:
            results.append(
                {"object": None, "passed": False, "error": "object entry missing name"}
            )
            passed_all = False
            continue

        harness = repo_root / "objects" / name / "eval" / "run_harness.py"
        if not harness.exists():
            results.append(
                {"object": name, "passed": False, "error": "missing eval harness"}
            )
            passed_all = False
            continue

        res = run_harness(repo_root, harness, args.write_evidence, args.deterministic)
        res["object"] = name
        passed_all = (
            passed_all and bool(res.get("passed")) and int(res.get("score", 0)) == 100
        )
        results.append(res)

    out = {
        "passed": passed_all,
        "objects_total": len(results),
        "objects_passed": sum(
            1 for r in results if r.get("passed") and int(r.get("score", 0)) == 100
        ),
        "results": [
            {
                k: v
                for k, v in r.items()
                if k in {"object", "passed", "score", "error", "returncode"}
            }
            for r in results
        ],
    }
    print(json.dumps(out, indent=2, sort_keys=False))
    return 0 if passed_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
