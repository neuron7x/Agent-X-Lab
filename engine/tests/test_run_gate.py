from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = REPO_ROOT.parent


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


def _run_with_relative_evidence_file(
    run_cwd: Path,
    target_cwd: Path,
    evidence_file: str,
    stdout: Path,
    stderr: Path,
) -> None:
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
            "--evidence-file",
            evidence_file,
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


def _candidate_evidence_paths(rel: str) -> list[Path]:
    return [REPO_ROOT / rel, MONOREPO_ROOT / rel]


def _existing_evidence_path(rel: str) -> Path | None:
    for path in _candidate_evidence_paths(rel):
        if path.exists():
            return path
    return None


def test_run_gate_writes_default_evidence_under_repo_root(tmp_path: Path) -> None:
    target_cwd = REPO_ROOT / "tests"
    run_cwd = tmp_path / "outside"
    run_cwd.mkdir()

    rel = "artifacts/agent/evidence.jsonl"
    evidence = _existing_evidence_path(rel) or _candidate_evidence_paths(rel)[0]
    before = evidence.read_text(encoding="utf-8") if evidence.exists() else ""

    _run_with_cwd(
        run_cwd=run_cwd,
        target_cwd=target_cwd,
        stdout=tmp_path / "out1.txt",
        stderr=tmp_path / "err1.txt",
    )

    evidence_after = _existing_evidence_path(rel)
    if evidence_after is not None and evidence_after.exists():
        after = evidence_after.read_text(encoding="utf-8")
        assert len(after) >= len(before)
    assert not (run_cwd / rel).exists()


def test_run_gate_default_evidence_path_stable_across_cwds(tmp_path: Path) -> None:
    target_cwd = REPO_ROOT / "tests"
    rel = "artifacts/agent/evidence.jsonl"
    evidence = _existing_evidence_path(rel) or _candidate_evidence_paths(rel)[0]
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

    evidence_after = _existing_evidence_path(rel)
    if evidence_after is not None and evidence_after.exists():
        lines = evidence_after.read_text(encoding="utf-8")[len(start) :].strip().splitlines()
        if lines:
            assert not (run_cwd_a / rel).exists()
    assert not (run_cwd_b / rel).exists()


def test_run_gate_relative_evidence_file_is_repo_root_anchored(tmp_path: Path) -> None:
    target_cwd = REPO_ROOT / "tests"
    run_cwd = tmp_path / "outside"
    run_cwd.mkdir()

    rel_evidence = "artifacts/agent/custom-evidence.jsonl"
    for path in _candidate_evidence_paths(rel_evidence):
        if path.exists():
            path.unlink()

    _run_with_relative_evidence_file(
        run_cwd=run_cwd,
        target_cwd=target_cwd,
        evidence_file=rel_evidence,
        stdout=tmp_path / "out_custom.txt",
        stderr=tmp_path / "err_custom.txt",
    )

    assert _existing_evidence_path(rel_evidence) is not None
    assert not (run_cwd / rel_evidence).exists()
