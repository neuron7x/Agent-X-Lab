from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def test_prompt_lint_passes_repo_paths() -> None:
    p = run(["python", "tools/prompt_lint.py", "--paths", "catalog", "docs"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_prompt_lint_detects_bad_identifier_policy() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "bad.txt"
        test_file.write_text("agent_id: Bad-Hyphen-Id\n", encoding="utf-8")

        p = run(["python", str(REPO_ROOT / "tools/prompt_lint.py"), "--paths", str(test_file)], cwd=Path(temp_dir))
        assert p.returncode == 1
        assert "E_ID_POLICY" in p.stdout
