from __future__ import annotations

from pathlib import Path

from exoneural_governor._exec import run_command
from exoneural_governor.contract_eval import _sha256_file
from exoneural_governor.repo_model import _canon_rel, _match


def test_run_command_missing_binary_is_structured() -> None:
    rec = run_command("missing", ["definitely-not-a-real-binary-codex"], Path.cwd())
    assert rec.returncode == 127
    assert rec.stderr.startswith("ENOENT:")


def test_streaming_sha256_matches_known_value(tmp_path: Path) -> None:
    p = tmp_path / "big.bin"
    p.write_bytes((b"abc123\n" * 10000))
    got = _sha256_file(p)
    import hashlib

    exp = hashlib.sha256(p.read_bytes()).hexdigest()
    assert got == exp


def test_glob_match_windows_normalization() -> None:
    rel = _canon_rel(r"engine\tools\nested\runner.py")
    assert rel == "engine/tools/nested/runner.py"
    assert _match(rel, "engine/tools/**/*.py")
