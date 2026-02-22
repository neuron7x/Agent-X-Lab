from __future__ import annotations

import sys
from pathlib import Path

from tools import feg_r8_verify


def test_run_treats_shell_metacharacters_as_literal_arguments(tmp_path: Path) -> None:
    sentinel = tmp_path / "should_not_exist"
    payload = f"literal;touch {sentinel}"
    result = feg_r8_verify.run(
        [sys.executable, "-c", "import sys;print(sys.argv[1])", payload]
    )

    assert result["exit"] == 0
    assert not sentinel.exists()
    assert result["cmd"]
    assert isinstance(result["log_tail"], list)
