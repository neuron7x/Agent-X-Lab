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


def run_command(name: str, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> ExecResult:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    proc = subprocess.run(command, cwd=cwd, env=run_env, capture_output=True, text=True, check=False)
    return ExecResult(name=name, command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


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
