from __future__ import annotations

from pathlib import Path

from tools.titan9_inventory import _parse_workflow_commands


def test_inventory_normalizes_inline_scripts(tmp_path: Path) -> None:
    wf = tmp_path / "a.yml"
    wf.write_text(
        """
name: t
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python -c \"print('super-secret-body')\"
""",
        encoding="utf-8",
    )
    commands = _parse_workflow_commands(tmp_path)
    assert any(c.startswith("inline-script sha256:") for c in commands)
    assert not any("super-secret-body" in c for c in commands)


def test_inventory_ignores_heredoc_body(tmp_path: Path) -> None:
    wf = tmp_path / "b.yml"
    wf.write_text(
        """
name: t
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cat > out.json <<'JSON'
          {"very":"large-body"}
          JSON
          echo done
""",
        encoding="utf-8",
    )
    commands = _parse_workflow_commands(tmp_path)
    assert "cat > out.json <<'JSON'" in commands
    assert "echo done" in commands
    assert not any("large-body" in c for c in commands)


def test_inventory_normalizes_bash_c_inline(tmp_path: Path) -> None:
    wf = tmp_path / "c.yml"
    wf.write_text(
        """
name: t
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: |
          bash -c "echo dangerous"
""",
        encoding="utf-8",
    )
    commands = _parse_workflow_commands(tmp_path)
    assert any(c.startswith("inline-script sha256:") for c in commands)
    assert not any("dangerous" in c for c in commands)
