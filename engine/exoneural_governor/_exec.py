from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EnvPolicy:
    allowlist_keys: set[str]
    defaults: dict[str, str]
    required_keys: set[str]


DEFAULT_ENV_POLICY = EnvPolicy(
    allowlist_keys={
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "TERM",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SystemRoot",
        "WINDIR",
        "ComSpec",
        "PATHEXT",
    },
    defaults={
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TZ": "UTC",
        "NO_COLOR": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "PYTHONHASHSEED": "0",
    },
    required_keys={"PATH"},
)


@dataclass(frozen=True)
class ExecResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, Any]:
        stdout_b = self.stdout.encode("utf-8", errors="replace")
        stderr_b = self.stderr.encode("utf-8", errors="replace")
        return {
            "name": self.name,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_sha256": hashlib.sha256(stdout_b).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_b).hexdigest(),
        }


def build_env(extra_env: dict[str, str] | None = None, policy: EnvPolicy = DEFAULT_ENV_POLICY) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in sorted(policy.allowlist_keys):
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    for key, value in policy.defaults.items():
        env.setdefault(key, value)
    if extra_env:
        for key, value in extra_env.items():
            env[key] = value

    if not env.get("PATH"):
        env["PATH"] = os.defpath

    missing = sorted([k for k in policy.required_keys if not env.get(k)])
    if missing:
        raise RuntimeError(f"missing required environment keys: {','.join(missing)}")
    return env


def run_command(name: str, command: list[str], cwd: Path, env: dict[str, str] | None = None, policy: EnvPolicy = DEFAULT_ENV_POLICY) -> ExecResult:
    run_env = build_env(extra_env=env, policy=policy)
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            env=run_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return ExecResult(name=name, command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    except FileNotFoundError:
        binary = command[0] if command else "<empty>"
        return ExecResult(name=name, command=command, returncode=127, stdout="", stderr=f"ENOENT:{binary}")
    except OSError as exc:
        binary = command[0] if command else "<empty>"
        return ExecResult(name=name, command=command, returncode=127, stdout="", stderr=f"OSERROR:{binary}:{exc}")


def python_module_cmd(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


def pip_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "pip", *args]


def write_command_artifacts(out_dir: Path, records: list[ExecResult]) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    lines: list[str] = []
    for idx, rec in enumerate(records, start=1):
        prefix = f"{idx:03d}_{rec.name}"
        out_json = out_dir / f"{prefix}.json"
        out_json.write_text(json.dumps(rec.as_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        files.append(out_json.name)
        lines.append(json.dumps({"name": rec.name, "command": rec.command}, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    (out_dir / "commands.log").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    files.append("commands.log")
    return sorted(files)
