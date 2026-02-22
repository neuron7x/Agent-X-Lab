from __future__ import annotations

from unittest.mock import patch

from exoneural_governor import network
from exoneural_governor import backend


def test_accelerated_backend_requires_torch_with_stable_error_message() -> None:
    with patch.object(backend, "_torch_available", return_value=False):
        msgs = []
        for _ in range(3):
            try:
                network.validate_backend("accelerated")
            except RuntimeError as err:
                msgs.append(str(err))
            else:
                raise AssertionError("Expected RuntimeError when torch is missing")

    assert msgs[0] == msgs[1] == msgs[2]
    assert "E_BACKEND_TORCH_MISSING" in msgs[0]


def test_reference_backend_does_not_require_torch() -> None:
    with patch.object(backend, "_torch_available", return_value=False):
        network.validate_backend("reference")
