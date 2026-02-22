from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_with_cwd(run_cwd: Path, target_cwd: Path, stdout: Path, stderr: Path) -> None:
    proc = subprocess.run(
        [
            "python",
            str(REPO_ROOT / "tools" / "run_gate.py"),
            "--gate-id",
            "T",
            "--cwd",
            str(target_cwd),
            "--stdout",
            str(stdout),
            "--stderr",
            str(stderr),
            "--",
            "python",
            "-c",
            "print('ok')",
        ],
        cwd=run_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr


def test_run_gate_writes_default_evidence_under_repo_root(tmp_path: Path) -> None:
    target_cwd = REPO_ROOT / "tests"
    run_cwd = tmp_path / "outside"
    run_cwd.mkdir()

    evidence = REPO_ROOT / "artifacts" / "agent" / "evidence.jsonl"
    before = evidence.read_text(encoding="utf-8") if evidence.exists() else ""

    _run_with_cwd(
        run_cwd=run_cwd,
        target_cwd=target_cwd,
        stdout=tmp_path / "out1.txt",
        stderr=tmp_path / "err1.txt",
    )

    assert evidence.exists()
    after = evidence.read_text(encoding="utf-8")
    assert len(after) > len(before)
    assert not (run_cwd / "artifacts" / "agent" / "evidence.jsonl").exists()


def test_run_gate_default_evidence_path_stable_across_cwds(tmp_path: Path) -> None:
    target_cwd = REPO_ROOT / "tests"
    evidence = REPO_ROOT / "artifacts" / "agent" / "evidence.jsonl"

    start = evidence.read_text(encoding="utf-8") if evidence.exists() else ""

    run_cwd_a = tmp_path / "a"
    run_cwd_b = tmp_path / "b"
    run_cwd_a.mkdir()
    run_cwd_b.mkdir()

    _run_with_cwd(
        run_cwd=run_cwd_a,
        target_cwd=target_cwd,
        stdout=tmp_path / "out_a.txt",
        stderr=tmp_path / "err_a.txt",
    )
    _run_with_cwd(
        run_cwd=run_cwd_b,
        target_cwd=target_cwd,
        stdout=tmp_path / "out_b.txt",
        stderr=tmp_path / "err_b.txt",
    )

    lines = evidence.read_text(encoding="utf-8")[len(start) :].strip().splitlines()
    assert len(lines) >= 2
    assert not (run_cwd_a / "artifacts" / "agent" / "evidence.jsonl").exists()
    assert not (run_cwd_b / "artifacts" / "agent" / "evidence.jsonl").exists()
    _ = json.loads(lines[-1])
