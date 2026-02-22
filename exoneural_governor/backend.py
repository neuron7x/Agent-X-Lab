from __future__ import annotations

import importlib

from .util import log_event, setup_json_logger


E_BACKEND_TORCH_MISSING = "E_BACKEND_TORCH_MISSING"
BACKEND_TORCH_MISSING_MESSAGE = (
    "E_BACKEND_TORCH_MISSING: accelerated backend requires torch. "
    "Fix: install torch or use backend='reference'."
)

_LOG = setup_json_logger("exoneural_governor.backend")


def _torch_available() -> bool:
    try:
        importlib.import_module("torch")
    except Exception:
        log_event(_LOG, "backend.torch.check", available=False)
        return False
    log_event(_LOG, "backend.torch.check", available=True)
    return True


def resolve_backend(backend: str) -> str:
    log_event(_LOG, "backend.resolve.start", backend=backend)
    if backend == "accelerated" and not _torch_available():
        log_event(
            _LOG,
            "backend.resolve.failure",
            backend=backend,
            error_code=E_BACKEND_TORCH_MISSING,
        )
        raise RuntimeError(BACKEND_TORCH_MISSING_MESSAGE)
    log_event(_LOG, "backend.resolve.success", backend=backend)
    return backend
