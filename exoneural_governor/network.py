from __future__ import annotations

from exoneural_governor.backend import BACKEND_TORCH_MISSING_MESSAGE
from exoneural_governor.util import log_event, setup_json_logger

_LOG = setup_json_logger("exoneural_governor.network")

try:
    import torch as _torch  # noqa: F401

    HAS_TORCH = True
except Exception:
    HAS_TORCH = False


log_event(_LOG, "network.torch.detected", has_torch=HAS_TORCH)


def validate_backend(backend: str) -> None:
    log_event(_LOG, "network.backend.validate.start", backend=backend)
    if backend == "accelerated" and not HAS_TORCH:
        log_event(
            _LOG,
            "network.backend.validate.failure",
            backend=backend,
            error_code="E_BACKEND_TORCH_MISSING",
        )
        raise RuntimeError(BACKEND_TORCH_MISSING_MESSAGE)
    log_event(_LOG, "network.backend.validate.success", backend=backend)
