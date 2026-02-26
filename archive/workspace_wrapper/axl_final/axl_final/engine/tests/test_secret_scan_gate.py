from __future__ import annotations

from pathlib import Path

from tools.secret_scan_gate import _scan_file


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
