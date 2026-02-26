from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.backend import (
    BACKEND_TORCH_MISSING_MESSAGE,
    E_BACKEND_TORCH_MISSING,
    resolve_backend,
)


def test_accelerated_backend_without_torch_raises_runtime_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'torch'")

    monkeypatch.setattr(importlib, "import_module", _raise)

    with pytest.raises(RuntimeError) as exc:
        resolve_backend("accelerated")

    msg = str(exc.value)
    assert isinstance(exc.value, RuntimeError)
    assert E_BACKEND_TORCH_MISSING in msg
    assert msg == BACKEND_TORCH_MISSING_MESSAGE


def test_accelerated_backend_missing_torch_message_is_stable_across_three_retries(
    monkeypatch,
):
    def _raise(*args, **kwargs):
        raise RuntimeError("torch import failed")

    monkeypatch.setattr(importlib, "import_module", _raise)

    errors: list[str] = []
    for _ in range(3):
        with pytest.raises(RuntimeError) as exc:
            resolve_backend("accelerated")
        errors.append(str(exc.value))

    assert len(set(errors)) == 1
    assert errors[0] == BACKEND_TORCH_MISSING_MESSAGE
