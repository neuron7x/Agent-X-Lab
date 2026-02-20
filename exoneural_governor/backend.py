from __future__ import annotations

import importlib


E_BACKEND_TORCH_MISSING = "E_BACKEND_TORCH_MISSING"
BACKEND_TORCH_MISSING_MESSAGE = (
    "E_BACKEND_TORCH_MISSING: accelerated backend was requested without torch availability."
)


def _torch_available() -> bool:
    try:
        importlib.import_module("torch")
    except Exception:
        return False
    return True


def resolve_backend(backend: str) -> str:
    if backend == "accelerated" and not _torch_available():
        raise RuntimeError(BACKEND_TORCH_MISSING_MESSAGE)
    return backend

