from __future__ import annotations

import json
from pathlib import Path

from .catalog import validate_catalog
from .config import Config
from .inventory import inventory
from .manifest import write_manifest
from .redaction import load_redaction_patterns, redact_tree
from .util import sha256_bytes, utc_now_iso, write_json, run_cmd, ensure_dir


def _work_id(repo_root: Path, cfg: Config) -> str:
    # Prefer git HEAD when available; otherwise derive a stable local fingerprint.
    tmp_dir = repo_root / "artifacts" / "tmp"
    ensure_dir(tmp_dir)
    head = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_root, stdout_path=tmp_dir / "head.stdout", stderr_path=tmp_dir / "head.stderr")
    if head.exit_code == 0:
        head_sha = (tmp_dir / "head.stdout").read_text(encoding="utf-8", errors="replace").strip()
    else:
        # Fail-soft here: project scaffolds may run before git init.
        head_sha = "NO_GIT"

    # Include catalog index hash for stability.
    idx = (repo_root / "catalog" / "index.json")
    idx_hash = sha256_bytes(idx.read_bytes()) if idx.exists() else "NO_INDEX"

    payload = json.dumps({
        "head": head_sha,
        "catalog_index": idx_hash,
        "config": {
            "artifact_name": cfg.artifact_name,
            "baseline_commands": cfg.baseline_commands,
        },
    }, sort_keys=True).encode("utf-8")
    return sha256_bytes(payload)[:16]


def run_vr(cfg: Config, *, write_back: bool = True) -> dict:
    repo_root = cfg.repo_root
    work_id = _work_id(repo_root, cfg)
    date = utc_now_iso()[:10].replace("-", "")
    evidence_root = cfg.evidence_root_base / date / work_id
    reports_dir = evidence_root / "REPORTS"
    cmds_dir = evidence_root / "COMMANDS"
    ensure_dir(reports_dir)
    ensure_dir(cmds_dir)

    patterns = load_redaction_patterns(cfg.redaction_policy_path)

    inv = inventory(repo_root, reports_dir / "inventory")
    cat = validate_catalog(repo_root)

    # Baseline commands (default: pytest)
    cmd_results = []
    for i, argv in enumerate(cfg.baseline_commands):
        res = run_cmd(argv, cwd=repo_root, stdout_path=cmds_dir / f"{i:03d}.stdout.txt", stderr_path=cmds_dir / f"{i:03d}.stderr.txt")
        cmd_results.append(res.__dict__)

    # Redact captured evidence
    redaction_changed = redact_tree(evidence_root, patterns)
    write_json(reports_dir / "redaction.changed.json", {"changed": redaction_changed, "count": len(redaction_changed)})

    man = write_manifest(evidence_root, reports_dir / "MANIFEST.json")

    # Compute metrics (deterministic, local)
    all_exit_codes = [int(r["exit_code"]) for r in cmd_results]
    pass_rate = 1.0 if all(x == 0 for x in all_exit_codes) else 0.0

    vr = {
        "schema": "VR-2026.1",
        "utc": utc_now_iso(),
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
            "inventory": str((reports_dir / "inventory" / "inventory.json").relative_to(repo_root)),
            "catalog_validation": str((repo_root / "artifacts" / "reports" / "catalog.validate.json").relative_to(repo_root)),
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
        (repo_root / "VR.json").write_text(json.dumps(vr, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return vr
