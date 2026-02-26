from __future__ import annotations

from exoneural_governor.backend import BACKEND_TORCH_MISSING_MESSAGE

try:
    import torch as _torch  # noqa: F401

    HAS_TORCH = True
except Exception:
    HAS_TORCH = False


def validate_backend(backend: str) -> None:
    if backend == "accelerated" and not HAS_TORCH:
        raise RuntimeError(BACKEND_TORCH_MISSING_MESSAGE)
