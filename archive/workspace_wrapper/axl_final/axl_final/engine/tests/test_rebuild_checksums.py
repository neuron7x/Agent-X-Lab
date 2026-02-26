from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_rebuild(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/rebuild_checksums.py",
            "--repo-root",
            str(repo_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_rebuild_checksums_excludes_transient_artifact_paths(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    (tmp_path / "artifacts/security").mkdir(parents=True)
    (tmp_path / "artifacts/titan9").mkdir(parents=True)
    (tmp_path / "artifacts/reports").mkdir(parents=True)
    (tmp_path / "objects/x/artifacts/evidence/reference/eval").mkdir(parents=True)
    (tmp_path / "src").mkdir(parents=True)

    (tmp_path / "src/stable.txt").write_text("stable\n", encoding="utf-8")
    (tmp_path / "artifacts/security/pip-audit.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (tmp_path / "artifacts/titan9/proof.log").write_text("proof\n", encoding="utf-8")
    (tmp_path / "artifacts/reports/summary.log").write_text(
        "report\n", encoding="utf-8"
    )
    ref_report = tmp_path / "objects/x/artifacts/evidence/reference/eval/report.json"
    ref_report.write_text('{"passed": true}\n', encoding="utf-8")

    (tmp_path / "MANIFEST.json").write_text(
        json.dumps(
            {
                "arsenal": {},
                "objects": [],
                "protocols": [],
                "architecture": [],
                "metrics": {},
                "checksums": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "git",
            "add",
            "src/stable.txt",
            "objects/x/artifacts/evidence/reference/eval/report.json",
            "MANIFEST.json",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    proc = run_rebuild(tmp_path)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    manifest = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
    checksums = manifest["checksums"]
    assert "src/stable.txt" in checksums
    assert "objects/x/artifacts/evidence/reference/eval/report.json" in checksums

    bad_prefixes = [
        "artifacts/security/",
        "artifacts/titan9/",
        "artifacts/reports/",
    ]
    bad_paths = [
        path
        for path in checksums
        if any(path.startswith(prefix) for prefix in bad_prefixes)
    ]
    assert bad_paths == [], f"transient artifact paths must be excluded: {bad_paths}"


def test_rebuild_checksums_uses_git_tracked_files_only(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    (tmp_path / "MANIFEST.json").write_text(
        json.dumps(
            {
                "arsenal": {},
                "objects": [],
                "protocols": [],
                "architecture": [],
                "metrics": {},
                "checksums": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "tracked.txt", "MANIFEST.json"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    (tmp_path / "untracked.txt").write_text("temp\n", encoding="utf-8")

    proc = run_rebuild(tmp_path)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    manifest = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
    checksums = manifest["checksums"]
    assert "tracked.txt" in checksums
    assert "untracked.txt" not in checksums
