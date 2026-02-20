from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from .util import read_json

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "configs" / "sg.config.schema.json"


@dataclass(frozen=True)
class Config:
    repo_root: Path
    base_branch: str
    allowlist_globs: list[str]
    baseline_commands: list[list[str]]
    artifact_name: str
    budgets: dict[str, int]
    redaction_policy_path: Path
    evidence_root_base: Path


def load_config(path: Path) -> Config:
    raw = read_json(path)
    schema = read_json(SCHEMA_PATH)
    jsonschema.validate(instance=raw, schema=schema)

    # Deterministic path resolution:
    # - repo_root is resolved relative to the config file's directory
    # - other relative paths are resolved relative to repo_root
    base_dir = path.parent.resolve()
    rr = Path(str(raw["repo_root"]))
    repo_root = (base_dir / rr).resolve() if not rr.is_absolute() else rr.resolve()

    def _rel_to_repo(p: str) -> Path:
        q = Path(str(p))
        return (repo_root / q).resolve() if not q.is_absolute() else q.resolve()

    return Config(
        repo_root=repo_root,
        base_branch=str(raw.get("base_branch", "main")),
        allowlist_globs=list(raw["allowlist_globs"]),
        baseline_commands=[list(cmd) for cmd in raw["baseline_commands"]],
        artifact_name=str(raw["artifact_name"]),
        budgets=dict(raw["budgets"]),
        redaction_policy_path=_rel_to_repo(str(raw.get("redaction_policy_path", "SECURITY.redaction.yml"))),
        evidence_root_base=_rel_to_repo(str(raw.get("evidence_root_base", "artifacts/evidence"))),
    )
