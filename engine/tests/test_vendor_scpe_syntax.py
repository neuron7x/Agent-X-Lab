from __future__ import annotations

import py_compile
from pathlib import Path


def test_vendor_scpe_run_interpreter_is_syntax_valid() -> None:
    target = (
        Path(__file__).resolve().parents[1]
        / "vendor/scpe-cimqa-2026.3.0/tools/run_interpreter.py"
    )
    py_compile.compile(str(target), doraise=True)
