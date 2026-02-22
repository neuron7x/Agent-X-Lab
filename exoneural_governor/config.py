from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import jsonschema

from .util import read_json

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "configs" / "sg.config.schema.json"
ENV_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "environments"
    / "environment.schema.json"
)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:secret|token|password|passwd|private[_-]?key|api[_-]?key)",
    re.IGNORECASE,
)
ALLOWED_SECRET_VALUE_PATTERN = re.compile(
    r"^(\$\{[A-Z][A-Z0-9_]*\}|sm://[a-zA-Z0-9._/-]+)$"
)


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
    env_name: str
    env_profile: dict


def _assert_no_inline_secrets(node, path: str = "$") -> None:
    if isinstance(node, dict):
        for key in sorted(node.keys()):
            value = node[key]
            current_path = f"{path}.{key}"
            if SENSITIVE_KEY_PATTERN.search(key) and not isinstance(value, (dict, list)):
                if not isinstance(value, str) or not ALLOWED_SECRET_VALUE_PATTERN.fullmatch(
                    value
                ):
                    raise ValueError(
                        f"inline secret-like value is not allowed at {current_path}; use environment variable or secret-manager binding"
                    )
            _assert_no_inline_secrets(value, current_path)
        return

    if isinstance(node, list):
        for index, value in enumerate(node):
            _assert_no_inline_secrets(value, f"{path}[{index}]")


def load_config(path: Path, *, env: str) -> Config:
    if not env:
        raise ValueError("environment must be explicitly provided")

    raw = read_json(path)
    schema = read_json(SCHEMA_PATH)
    jsonschema.validate(instance=raw, schema=schema)
    _assert_no_inline_secrets(raw)

    # Deterministic path resolution:
    # - repo_root is resolved relative to the config file's directory
    # - other relative paths are resolved relative to repo_root
    base_dir = path.parent.resolve()
    rr = Path(str(raw["repo_root"]))
    repo_root = (base_dir / rr).resolve() if not rr.is_absolute() else rr.resolve()

    def _rel_to_repo(p: str) -> Path:
        q = Path(str(p))
        return (repo_root / q).resolve() if not q.is_absolute() else q.resolve()

    env_profiles = dict(raw["environment_profiles"])
    if env not in env_profiles:
        raise ValueError(f"unknown environment {env!r}; expected one of {sorted(env_profiles)}")

    env_profile_path = _rel_to_repo(str(env_profiles[env]))
    env_profile = read_json(env_profile_path)
    env_schema = read_json(ENV_SCHEMA_PATH)
    jsonschema.validate(instance=env_profile, schema=env_schema)
    _assert_no_inline_secrets(env_profile, f"$.environment_profiles.{env}")

    if env_profile.get("name") != env:
        raise ValueError(
            f"environment profile mismatch: requested {env!r}, file declares {env_profile.get('name')!r}"
        )

    return Config(
        repo_root=repo_root,
        base_branch=str(raw.get("base_branch", "main")),
        allowlist_globs=list(raw["allowlist_globs"]),
        baseline_commands=[list(cmd) for cmd in raw["baseline_commands"]],
        artifact_name=str(raw["artifact_name"]),
        budgets=dict(raw["budgets"]),
        redaction_policy_path=_rel_to_repo(
            str(raw.get("redaction_policy_path", "SECURITY.redaction.yml"))
        ),
        evidence_root_base=_rel_to_repo(
            str(raw.get("evidence_root_base", "artifacts/evidence"))
        ),
        env_name=env,
        env_profile=env_profile,
    )
