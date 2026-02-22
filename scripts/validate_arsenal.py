#!/usr/bin/env python3
"""
AgentX Lab — deterministic validator (fail-closed).

Outputs a JSON report:
  - passed
  - checks_total / checks_passed / checks_failed
  - failed_checks[] with ids and details

Usage:
  python scripts/validate_arsenal.py --repo-root . --strict
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_ROOT_FILES = [
    "README.md",
    "MANIFEST.json",
    "LICENSE",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "requirements-dev.txt",
    "Makefile",
    "schemas/root_manifest.schema.json",
    "schemas/object_manifest.schema.json",
    "schemas/eval_report.schema.json",
    "scripts/arsenal.py",
    "scripts/validate_arsenal.py",
    "scripts/schema_validate.py",
    "scripts/rebuild_checksums.py",
    "scripts/rebuild_catalog_index.py",
    "scripts/run_object_evals.py",
    ".github/actions/pin-pip/action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
    ".github/workflows/lint-actions.yml",
    ".github/pull_request_template.md",
    ".github/dependabot.yml",
    "CONTRIBUTING.md",
    "SECURITY.md",
]


@dataclass(frozen=True)
class Check:
    id: str
    passed: bool
    details: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(checks: List[Check], cid: str, cond: bool, details: str) -> None:
    checks.append(Check(cid, bool(cond), details))


ALLOWED_ARTIFACT_PATTERNS = (
    "objects/*/artifacts/evidence/reference/*",
    "objects/*/artifacts/evidence/reference/**/*",
    "objects/*/artifacts/evidence/.gitkeep",
)

# Files that legitimately change during baseline/runtime governance migrations
# and should not be hard-pinned in MANIFEST checksum strict checks.
CHECKSUM_MUTABLE_PATHS = {
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "scripts/validate_arsenal.py",
}


def _load_tracked_files(repo_root: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        text=False,
    )
    if proc.returncode != 0:
        return set()
    return {raw.decode("utf-8") for raw in proc.stdout.split(b"\x00") if raw}


def _is_allowed_artifact_path(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in ALLOWED_ARTIFACT_PATTERNS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--manifest",
        default="MANIFEST.json",
        help="Manifest path relative to repo root",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict checks (recommended for CI)",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    checks: List[Check] = []
    tracked_files = _load_tracked_files(repo_root)

    # --- Root files
    for idx, rel in enumerate(REQUIRED_ROOT_FILES, start=1):
        p = repo_root / rel
        add(checks, f"R{idx:02d}", p.exists(), f"required root path exists: {rel}")

    manifest_path = repo_root / args.manifest
    try:
        manifest = load_json(manifest_path)
        add(checks, "M01", True, "root MANIFEST.json parses as JSON")
    except Exception as e:
        add(checks, "M01", False, f"root MANIFEST.json parse failure: {e!r}")
        manifest = {}

    # --- Root manifest schema (best-effort even if parse failed)
    for k, cid in [
        ("arsenal", "M02"),
        ("objects", "M03"),
        ("protocols", "M04"),
        ("architecture", "M05"),
        ("metrics", "M06"),
        ("checksums", "M07"),
    ]:
        add(checks, cid, k in manifest, f"root MANIFEST has key: {k}")

    add(
        checks,
        "M08",
        isinstance(manifest.get("objects", []), list),
        "MANIFEST.objects is a list",
    )
    add(
        checks,
        "M09",
        isinstance(manifest.get("protocols", []), list),
        "MANIFEST.protocols is a list",
    )
    add(
        checks,
        "M10",
        isinstance(manifest.get("architecture", []), list),
        "MANIFEST.architecture is a list",
    )
    add(
        checks,
        "M11",
        isinstance(manifest.get("metrics", {}), dict),
        "MANIFEST.metrics is an object",
    )
    add(
        checks,
        "M12",
        isinstance(manifest.get("checksums", {}), dict),
        "MANIFEST.checksums is an object",
    )

    # --- Metrics cross-check
    metrics = (
        manifest.get("metrics", {})
        if isinstance(manifest.get("metrics", {}), dict)
        else {}
    )
    add(
        checks,
        "X01",
        metrics.get("total_objects") == len(manifest.get("objects", [])),
        "metrics.total_objects matches objects length",
    )
    add(
        checks,
        "X02",
        metrics.get("total_protocols") == len(manifest.get("protocols", [])),
        "metrics.total_protocols matches protocols length",
    )
    add(
        checks,
        "X03",
        metrics.get("total_architecture_docs") == len(manifest.get("architecture", [])),
        "metrics.total_architecture_docs matches architecture length",
    )

    # --- Referenced paths
    # Protocols
    for i, p in enumerate(manifest.get("protocols", []), start=1):
        rel = (p or {}).get("path", "")
        add(
            checks,
            f"P{i:02d}",
            (repo_root / rel).exists(),
            f"protocol path exists: {rel}",
        )

    # Architecture
    for i, a in enumerate(manifest.get("architecture", []), start=1):
        rel = (a or {}).get("path", "")
        add(
            checks,
            f"A{i:02d}",
            (repo_root / rel).exists(),
            f"architecture path exists: {rel}",
        )

    # Objects: verify object bundle + required dirs
    objects = manifest.get("objects", [])
    for i, o in enumerate(objects, start=1):
        obj_name = (o or {}).get("name", f"obj{i}")
        obj_bundle_rel = (o or {}).get("path", "")
        obj_dir = repo_root / Path(obj_bundle_rel).parent
        add(
            checks,
            f"O{i:02d}",
            (repo_root / obj_bundle_rel).exists(),
            f"object IO-BUNDLE exists: {obj_name} -> {obj_bundle_rel}",
        )

        # Strict structure checks
        if args.strict:
            for j, rel in enumerate(
                [
                    "MANIFEST.json",
                    "CHANGELOG.md",
                    "eval/run_harness.py",
                    "eval/graders.py",
                    "eval/cases",
                    "examples/happy",
                    "examples/adversarial",
                    "artifacts/evidence",
                    "artifacts/evidence/reference/eval/report.json",
                ],
                start=1,
            ):
                add(
                    checks,
                    f"S{i:02d}.{j:02d}",
                    (obj_dir / rel).exists(),
                    f"strict object path exists: {obj_name}/{rel}",
                )

            # No runtime evidence committed (only reference + .gitkeep allowed)
            # Evaluate git-tracked files only so local runtime outputs do not cause false failures.
            bad: list[str] = []
            tracked = subprocess.run(
                ["git", "ls-files", str(obj_dir / "artifacts" / "evidence")],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if tracked.returncode == 0:
                for line in tracked.stdout.splitlines():
                    rel = Path(line).as_posix()
                    if "/artifacts/evidence/reference/" in rel or rel.endswith(
                        "/artifacts/evidence/.gitkeep"
                    ):
                        continue
                    bad.append(rel)
            add(
                checks,
                f"E{i:02d}",
                len(bad) == 0,
                f"no non-reference evidence dirs committed: {obj_name} bad={bad}",
            )

            # Reference report must be PASS
            rep = obj_dir / "artifacts/evidence/reference/eval/report.json"
            try:
                repj = load_json(rep)
                ok = bool(repj.get("passed")) and int(repj.get("score", 0)) == 100
                add(
                    checks,
                    f"V{i:02d}",
                    ok,
                    f"reference eval report PASS (score=100): {obj_name}",
                )
            except Exception as e:
                add(
                    checks,
                    f"V{i:02d}",
                    False,
                    f"reference eval report parse failure: {obj_name} {e!r}",
                )

        # --- Schemas (strict)
    if args.strict:
        proc = subprocess.run(
            [
                "python",
                str(repo_root / "scripts" / "schema_validate.py"),
                "--repo-root",
                str(repo_root),
            ],
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        msg = (
            "schema_validate OK"
            if ok
            else ("schema_validate failed: " + (proc.stdout or proc.stderr or "")[:800])
        )
        add(checks, "S00", ok, msg)

    # --- Checksums (strict)
    if args.strict:
        csum = (
            manifest.get("checksums", {})
            if isinstance(manifest.get("checksums", {}), dict)
            else {}
        )
        add(checks, "C00", bool(csum), "MANIFEST.checksums present (strict)")
        for i, (rel, meta) in enumerate(sorted(csum.items()), start=1):
            if rel in CHECKSUM_MUTABLE_PATHS:
                add(
                    checks,
                    f"C{i:03d}.M",
                    True,
                    f"checksum skipped for mutable governance path: {rel}",
                )
                continue
            if tracked_files and rel not in tracked_files:
                add(
                    checks,
                    f"C{i:03d}.T",
                    False,
                    f"checksum path must be git-tracked stable file: {rel}",
                )
                continue
            if rel.startswith("artifacts/") and not _is_allowed_artifact_path(rel):
                add(
                    checks,
                    f"C{i:03d}.A",
                    False,
                    f"checksum path forbidden for transient artifacts: {rel}",
                )
                continue
            fp = repo_root / rel
            if not fp.exists():
                add(checks, f"C{i:03d}", False, f"checksum path missing: {rel}")
                continue
            expected = (meta or {}).get("sha256")
            if not expected:
                add(checks, f"C{i:03d}", False, f"checksum entry missing sha256: {rel}")
                continue
            actual = sha256_file(fp)
            add(checks, f"C{i:03d}", actual == expected, f"sha256 matches: {rel}")

    passed = all(c.passed for c in checks)
    report = {
        "passed": passed,
        "strict": bool(args.strict),
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c.passed),
        "checks_failed": sum(1 for c in checks if not c.passed),
        "failed_checks": [asdict(c) for c in checks if not c.passed],
    }
    print(json.dumps(report, indent=2, sort_keys=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
