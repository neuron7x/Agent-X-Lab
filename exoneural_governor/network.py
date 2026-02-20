from __future__ import annotations

try:
    import torch as _torch  # noqa: F401

    HAS_TORCH = True
except Exception:
    HAS_TORCH = False


def validate_backend(backend: str) -> None:
    if backend == "accelerated" and not HAS_TORCH:
        raise RuntimeError(
            "E_BACKEND_TORCH_MISSING: accelerated backend requires torch. "
            "Fix: install torch or use backend='reference'."
        )
