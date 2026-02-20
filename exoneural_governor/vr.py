from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from .catalog import validate_catalog
from .config import Config
from .inventory import inventory
from .manifest import write_manifest
from .redaction import load_redaction_patterns, redact_tree
from .util import sha256_bytes, write_json, run_cmd, ensure_dir


def _package_version(repo_root: Path) -> str:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return "0.0.0"
    raw = pyproject.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^version\s*=\s*"([^"]+)"', raw, flags=re.MULTILINE)
    if m:
        return m.group(1)
    return "0.0.0"


def _spec_token(repo_root: Path) -> str:
    spec = repo_root / "docs" / "SPEC.md"
    if not spec.exists():
        return "NO_SPEC"
    spec_text = spec.read_text(encoding="utf-8", errors="replace")
    marker = re.search(
        r"^\s*(TITAN-9\s+[A-Za-z0-9._-]+\s+Protocol\s+Spec)\s*$",
        spec_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if marker:
        return re.sub(r"\s+", " ", marker.group(1).strip()).upper()
    return sha256_bytes(spec.read_bytes())


def _evidence_tag(work_id: str) -> str:
    return f"run-{sha256_bytes(work_id.encode('utf-8'))[:12]}"


def _work_id(repo_root: Path, cfg: Config) -> str:
    # Prefer git HEAD when available; otherwise require BUILD_ID and derive a stable fingerprint.
    tmp_dir = repo_root / "artifacts" / "tmp"
    ensure_dir(tmp_dir)
    head = run_cmd(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        stdout_path=tmp_dir / "head.stdout",
        stderr_path=tmp_dir / "head.stderr",
    )
    if head.exit_code == 0:
        git_commit = (
            (tmp_dir / "head.stdout")
            .read_text(encoding="utf-8", errors="replace")
            .strip()
        )
        if git_commit:
            return git_commit

    build_id = os.environ.get("BUILD_ID", "").strip()
    if not build_id:
        raise ValueError(
            "E_NO_GIT_NO_BUILD_ID: git commit unavailable; set BUILD_ID for deterministic provenance id."
        )

    pyproject = repo_root / "pyproject.toml"
    pyproject_bytes = pyproject.read_bytes() if pyproject.exists() else b""
    version = _package_version(repo_root)
    spec_token = _spec_token(repo_root).encode("utf-8")

    digest = sha256_bytes(
        b"\n".join(
            [
                pyproject_bytes,
                spec_token,
                version.encode("utf-8"),
                build_id.encode("utf-8"),
            ]
        )
    )[:32]
    return f"release-{version}+nogit.{digest}"


def run_vr(cfg: Config, *, write_back: bool = True) -> dict:
    repo_root = cfg.repo_root
    work_id = _work_id(repo_root, cfg)
    evidence_root = cfg.evidence_root_base / _evidence_tag(work_id) / work_id
    reports_dir = evidence_root / "REPORTS"
    cmds_dir = evidence_root / "COMMANDS"
    ensure_dir(reports_dir)
    ensure_dir(cmds_dir)

    patterns = load_redaction_patterns(cfg.redaction_policy_path)

    inventory(repo_root, reports_dir / "inventory")
    cat = validate_catalog(repo_root)

    # Baseline commands (default: pytest)
    cmd_results = []
    for i, argv in enumerate(cfg.baseline_commands):
        res = run_cmd(
            argv,
            cwd=repo_root,
            stdout_path=cmds_dir / f"{i:03d}.stdout.txt",
            stderr_path=cmds_dir / f"{i:03d}.stderr.txt",
        )
        cmd_results.append(res.__dict__)

    # Redact captured evidence
    redaction_changed = redact_tree(evidence_root, patterns)
    write_json(
        reports_dir / "redaction.changed.json",
        {"changed": redaction_changed, "count": len(redaction_changed)},
    )

    man = write_manifest(evidence_root, reports_dir / "MANIFEST.json")

    # Compute metrics (deterministic, local)
    all_exit_codes = [int(r["exit_code"]) for r in cmd_results]
    pass_rate = 1.0 if all(x == 0 for x in all_exit_codes) else 0.0

    vr: Dict[str, Any] = {
        "schema": "VR-2026.1",
        "utc": "1970-01-01T00:00:00Z",
        "status": "RUN",
        "work_id": work_id,
        "evidence_root": str(evidence_root),
        "metrics": {
            "determinism": "ASSUMED_SINGLE_RUN",
            "catalog_ok": bool(cat["ok"]),
            "baseline_pass": all(x == 0 for x in all_exit_codes),
            "pass_rate": pass_rate,
            "evidence_manifest_entries": int(man["count"]),
        },
        "artifacts": {
            "inventory": str(
                (reports_dir / "inventory" / "inventory.json").relative_to(repo_root)
            ),
            "catalog_validation": str(
                (
                    repo_root / "artifacts" / "reports" / "catalog.validate.json"
                ).relative_to(repo_root)
            ),
            "manifest": str((reports_dir / "MANIFEST.json").relative_to(repo_root)),
        },
        "commands": cmd_results,
        "blockers": [],
    }

    # Fail-closed: if catalog invalid or baseline fails, set CALIBRATION_REQUIRED
    if not vr["metrics"]["catalog_ok"] or not vr["metrics"]["baseline_pass"]:
        vr["status"] = "CALIBRATION_REQUIRED"
        if not vr["metrics"]["catalog_ok"]:
            vr["blockers"].append("catalog_validation_failed")
        if not vr["metrics"]["baseline_pass"]:
            vr["blockers"].append("baseline_commands_failed")

    if write_back:
        (repo_root / "VR.json").write_text(
            json.dumps(vr, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return vr
