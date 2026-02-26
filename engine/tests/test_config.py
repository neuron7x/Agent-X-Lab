from __future__ import annotations

import json
from pathlib import Path

import pytest

from exoneural_governor.config import load_config


def test_load_config_rejects_repo_root_without_pyproject(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    cfg_dir = repo / "configs"
    cfg_dir.mkdir(parents=True)

    schema_src = Path("configs/sg.config.schema.json")
    schema_dst = repo / "configs" / "sg.config.schema.json"
    schema_dst.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")

    cfg = {
        "repo_root": ".",
        "base_branch": "main",
        "allowlist_globs": ["README.md"],
        "baseline_commands": [["python", "-V"]],
        "artifact_name": "agentx-lab",
        "budgets": {"max_changed_files": 1, "max_changed_lines": 1},
        "redaction_policy_path": "SECURITY.redaction.yml",
        "evidence_root_base": "artifacts/evidence",
    }
    cfg_path = cfg_dir / "sg.config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="expected pyproject.toml"):
        load_config(cfg_path)
