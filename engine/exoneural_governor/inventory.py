from __future__ import annotations

from pathlib import Path

from .util import run_cmd, utc_now_iso, write_json


def inventory(repo_root: Path, out_dir: Path) -> dict:
    """Collect minimal deterministic inventory."""
    commands = [
        ["git", "rev-parse", "HEAD"],
        ["git", "status", "--porcelain"],
        ["python", "--version"],
        ["python", "-m", "pip", "--version"],
    ]
    results = []
    for i, argv in enumerate(commands):
        res = run_cmd(
            argv,
            cwd=repo_root,
            stdout_path=out_dir / f"cmd{i}.stdout.txt",
            stderr_path=out_dir / f"cmd{i}.stderr.txt",
        )
        results.append(res.__dict__)

    inv = {
        "utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "commands": results,
    }
    write_json(out_dir / "inventory.json", inv)
    return inv
