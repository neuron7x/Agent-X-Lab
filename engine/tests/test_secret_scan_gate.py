from __future__ import annotations

from pathlib import Path

from engine.tools.secret_scan_gate import _resolve_output_path, _scan_file


def test_scan_file_detects_private_key_pattern(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    findings = _scan_file(file, tmp_path)
    assert findings
    assert findings[0]["rule"] == "private_key"


def test_scan_file_ignores_safe_content(tmp_path: Path) -> None:
    file = tmp_path / "b.txt"
    file.write_text("hello world\n", encoding="utf-8")
    assert _scan_file(file, tmp_path) == []


def test_resolve_output_path_rejects_non_artifacts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "artifacts").mkdir()
    bad = tmp_path / "outside.json"
    try:
        _resolve_output_path(repo, bad)
    except ValueError as exc:
        assert "under artifacts" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_resolve_output_path_accepts_artifacts_relative(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out = _resolve_output_path(repo, Path("artifacts/security/secret-scan.json"))
    assert out == (repo / "artifacts/security/secret-scan.json").resolve()
