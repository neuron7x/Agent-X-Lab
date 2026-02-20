from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_proof_bundle.py"
)
SPEC = importlib.util.spec_from_file_location("generate_proof_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


CommandSpec = MODULE.CommandSpec
run_and_log = MODULE.run_and_log


def test_run_and_log_writes_command_exit_code_and_streams(tmp_path: Path) -> None:
    spec = CommandSpec(
        log_name="sample.log",
        command=["python", "-c", "print('ok')"],
    )

    exit_code = run_and_log(tmp_path, tmp_path, spec)

    assert exit_code == 0
    content = (tmp_path / "sample.log").read_text(encoding="utf-8")
    assert "command: python -c print('ok')" in content
    assert "exit_code: 0" in content
    assert "stdout:\nok" in content
    assert "stderr:\n<empty>" in content
