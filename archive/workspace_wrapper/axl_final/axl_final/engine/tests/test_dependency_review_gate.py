from __future__ import annotations

from pathlib import Path

from tools.dependency_review_gate import _check_file


def test_check_file_accepts_pinned_requirements(tmp_path: Path) -> None:
    req = tmp_path / "req.txt"
    req.write_text("pkg-a==1.2.3\n# comment\npkg_b==4.5.6\n", encoding="utf-8")
    assert _check_file(req) == []


def test_check_file_rejects_unpinned_and_vcs_lines(tmp_path: Path) -> None:
    req = tmp_path / "req.txt"
    req.write_text(
        "pkg-a>=1.2.3\n"
        "pkg-b @ https://example.com/pkg-b.whl\n"
        "git+https://github.com/example/repo.git\n",
        encoding="utf-8",
    )
    issues = _check_file(req)
    assert len(issues) == 3
    assert any("strictly pinned" in issue for issue in issues)
    assert any("non-hermetic" in issue for issue in issues)
