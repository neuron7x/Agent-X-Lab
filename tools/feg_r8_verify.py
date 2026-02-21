#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def run(cmd: str, cwd: Path | None = None) -> dict[str, Any]:
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=cwd)
    output = (p.stdout or "") + (p.stderr or "")
    tail_lines = output.splitlines()[-20:]
    tail = "\n".join(tail_lines)
    return {
        "cmd": cmd,
        "exit": p.returncode,
        "duration_s": round(time.time() - t0, 3),
        "log_tail": tail_lines,
        "log_tail_sha256": hashlib.sha256(tail.encode("utf-8")).hexdigest(),
    }


def git(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *cmd],
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return proc.stdout.strip()


def get_base_sha() -> str:
    try:
        return git(["rev-parse", "HEAD~1"])
    except subprocess.CalledProcessError:
        return git(["rev-parse", "HEAD"])


def get_candidate_files(base_sha: str) -> list[str]:
    names = git(["diff", "--name-only", f"{base_sha}..HEAD"])
    out: list[str] = []
    for name in names.splitlines():
        n = name.strip()
        if not n:
            continue
        if n.startswith("artifacts/"):
            continue
        out.append(n)
    return out


def run_required_gates(cwd: Path | None = None) -> list[dict[str, Any]]:
    gates = [
        "python tools/verify_workflow_hygiene.py",
        "python tools/verify_action_pinning.py",
        "python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json",
    ]
    return [run(cmd, cwd=cwd) for cmd in gates]


def all_pass(entries: list[dict[str, Any]]) -> bool:
    return all(int(entry.get("exit", 1)) == 0 for entry in entries)


def ablation_report(
    base_sha: str, outdir: Path, max_ablations: int
) -> dict[str, object]:
    candidates = get_candidate_files(base_sha)
    candidates = candidates[:max_ablations]
    trace_path = outdir / "minimality" / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "base_sha": base_sha,
        "head_sha": git(["rev-parse", "HEAD"]),
        "candidate_files": candidates,
        "ablation_results": [],
        "minimality_pass": True,
        "superfluous_files": [],
    }

    with tempfile.TemporaryDirectory(prefix="feg_r8_ablate_") as tmp:
        wt = Path(tmp) / "wt"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            for rel in candidates:
                file_path = wt / rel
                existed_in_base = (
                    subprocess.run(
                        ["git", "cat-file", "-e", f"{base_sha}:{rel}"],
                        cwd=wt,
                        check=False,
                        capture_output=True,
                        text=True,
                    ).returncode
                    == 0
                )

                if existed_in_base:
                    subprocess.run(
                        ["git", "checkout", base_sha, "--", rel],
                        cwd=wt,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                elif file_path.exists():
                    subprocess.run(
                        ["git", "rm", "-f", "--", rel],
                        cwd=wt,
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                gate_results = run_required_gates(cwd=wt)
                passes = all_pass(gate_results)
                row = {
                    "removed_file": rel,
                    "required_gates_pass": passes,
                    "gates": gate_results,
                }
                report["ablation_results"].append(row)  # type: ignore[index]
                with trace_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")

                if passes:
                    report["minimality_pass"] = False
                    report["superfluous_files"].append(rel)  # type: ignore[index]

                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=wt,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["git", "clean", "-ffd"],
                    cwd=wt,
                    check=True,
                    capture_output=True,
                    text=True,
                )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt)],
                check=True,
                capture_output=True,
                text=True,
            )

    (outdir / "minimality" / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--max-ablations", type=int, default=8)
    parser.add_argument("--enforce-minimality", action="store_true")
    args = parser.parse_args()

    outdir = Path("artifacts/feg_r8")
    outdir.mkdir(parents=True, exist_ok=True)

    gate_results = run_required_gates()
    gates_path = outdir / "gates.jsonl"
    gates_path.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in gate_results) + "\n",
        encoding="utf-8",
    )
    if not all_pass(gate_results):
        return 1

    minimality_ok = True
    if not args.skip_ablation:
        report = ablation_report(get_base_sha(), outdir, args.max_ablations)
        minimality_ok = bool(report.get("minimality_pass", False))

    witness = run("python tools/witness.py", cwd=Path.cwd())
    (outdir / "attestation" / "witness_runner.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (outdir / "attestation" / "witness_runner.json").write_text(
        json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if args.enforce_minimality and not minimality_ok:
        return 1
    return 0 if int(witness.get("exit", 1)) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
