#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--evidence", type=Path, default=Path("artifacts/agent/evidence.jsonl")
    )
    p.add_argument("--out", type=Path, default=Path("artifacts/agent/proof.json"))
    args = p.parse_args()

    lines = [
        line
        for line in args.evidence.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    entries = [json.loads(line) for line in lines]

    gates: list[dict[str, object]] = []
    all_ok = True
    for entry in entries:
        artifacts = []
        raw_artifacts = entry.get("artifacts", [])
        if not raw_artifacts and isinstance(entry.get("produced_paths"), list):
            raw_artifacts = [{"path": p} for p in entry.get("produced_paths", [])]
        for artifact in raw_artifacts:
            path = Path(artifact["path"])
            exists = path.exists()
            expected = artifact.get("sha256")
            is_proof_artifact = path.as_posix().endswith("artifacts/agent/proof.json")
            actual = (
                _sha256(path)
                if exists and path.is_file() and not is_proof_artifact
                else None
            )
            valid = (
                True if is_proof_artifact else (expected is None or actual == expected)
            )
            artifacts.append(
                {
                    "path": artifact["path"],
                    "exists": exists,
                    "sha256": actual,
                    "valid": valid,
                }
            )
            if not valid:
                all_ok = False
        if entry.get("exit_code", 0) != 0:
            all_ok = False
        gates.append(
            {
                "gate_id": entry.get("gate_id"),
                "command": entry.get("command"),
                "exit_code": entry.get("exit_code"),
                "stdout_path": entry.get("stdout_path"),
                "stderr_path": entry.get("stderr_path"),
                "artifacts": artifacts,
            }
        )

    proof = {
        "status": "pass" if all_ok else "fail",
        "evidence_path": str(args.evidence),
        "gates": gates,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
