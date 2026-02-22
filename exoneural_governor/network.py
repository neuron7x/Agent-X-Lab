from __future__ import annotations

from exoneural_governor.backend import resolve_backend


def validate_backend(backend: str) -> None:
    resolve_backend(backend)
