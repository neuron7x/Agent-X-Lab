from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__all__ = ["__version__"]
__version__ = "0.1.0"

__path__ = extend_path(__path__, __name__)
_engine_pkg = Path(__file__).resolve().parents[1] / "engine" / "exoneural_governor"
if _engine_pkg.exists():
    __path__.append(str(_engine_pkg))
