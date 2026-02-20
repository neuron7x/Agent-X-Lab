from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

TRACKED_HASH_PATHS = [
    "README.md",
    "docs/SPEC.md",
    "artifacts/titan9/inventory.json",
    "artifacts/titan9/readme_commands.json",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(repo_root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=3)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    out_dir = repo_root / "artifacts" / "titan9"
    out_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        [
            "python",
            "tools/titan9_inventory.py",
            "--repo-root",
            ".",
            "--out",
            "artifacts/titan9/inventory.json",
        ],
        [
            "python",
            "tools/verify_readme_contract.py",
            "--readme",
            "README.md",
            "--workflows",
            ".github/workflows",
            "--inventory",
            "artifacts/titan9/inventory.json",
        ],
    ]

    log_lines: list[str] = []
    cycle_hashes: list[tuple[str, str]] = []

    for index in range(1, args.cycles + 1):
        log_lines.append(f"=== cycle {index} ===")
        for command in commands:
            result = _run(repo_root, command)
            log_lines.append(f"$ {' '.join(command)}")
            if result.stdout.strip():
                log_lines.append(result.stdout.strip())
            if result.stderr.strip():
                log_lines.append(result.stderr.strip())
            if result.returncode != 0:
                (out_dir / "proof.log").write_text(
                    "\n".join(log_lines) + "\n",
                    encoding="utf-8",
                )
                return result.returncode

        inventory_hash = _sha256(out_dir / "inventory.json")
        commands_hash = _sha256(out_dir / "readme_commands.json")
        cycle_hashes.append((inventory_hash, commands_hash))
        log_lines.append(f"{inventory_hash}  artifacts/titan9/inventory.json")
        log_lines.append(f"{commands_hash}  artifacts/titan9/readme_commands.json")

    first = cycle_hashes[0]
    if any(current != first for current in cycle_hashes[1:]):
        log_lines.append("determinism_check=failed")
        (out_dir / "proof.log").write_text(
            "\n".join(log_lines) + "\n", encoding="utf-8"
        )
        return 1

    hashes = {
        rel_path: _sha256(repo_root / rel_path) for rel_path in TRACKED_HASH_PATHS
    }
    (out_dir / "hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "proof.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
