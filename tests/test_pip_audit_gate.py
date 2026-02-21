from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from tools import pip_audit_gate


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_allowlist_empty_when_missing(tmp_path: Path) -> None:
    assert pip_audit_gate._load_allowlist(tmp_path / "missing.json") == []


def test_load_allowlist_requires_fields(tmp_path: Path) -> None:
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(json.dumps({"ignore": [{"id": "CVE-1"}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        pip_audit_gate._load_allowlist(allowlist)


def test_split_allowlist_marks_expired_entries() -> None:
    entries = [
        pip_audit_gate.AllowEntry(
            vuln_id="CVE-2024-0001", reason="temp", expires=date(2099, 1, 1)
        ),
        pip_audit_gate.AllowEntry(
            vuln_id="CVE-2024-0002", reason="old", expires=date(2020, 1, 1)
        ),
    ]
    active, expired = pip_audit_gate._split_allowlist(entries, today=date(2026, 1, 1))
    assert active == ["CVE-2024-0001"]
    assert len(expired) == 1
    assert "CVE-2024-0002" in expired[0]


def test_main_writes_report_when_pip_audit_missing(tmp_path: Path) -> None:
    out = tmp_path / "pip-audit.json"
    allow = tmp_path / "allow.json"
    allow.write_text('{"ignore": []}\n', encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "tools/pip_audit_gate.py",
            "--requirements",
            "requirements.lock",
            "--allowlist",
            str(allow),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 3
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["reason"] == "pip_audit_missing"
