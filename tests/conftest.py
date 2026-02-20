from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import pytest

PRODUCT_MODULE_PREFIXES = (
    "exoneural_governor",
    "scripts",
)


@pytest.fixture(autouse=True)
def isolate_runtime_state() -> Iterator[None]:
    modules_before = set(sys.modules.keys())
    environ_before = dict(os.environ)

    yield

    new_product_modules = [
        module_name
        for module_name in sys.modules
        if module_name not in modules_before
        and module_name.startswith(PRODUCT_MODULE_PREFIXES)
    ]
    for module_name in new_product_modules:
        sys.modules.pop(module_name, None)

    os.environ.clear()
    os.environ.update(environ_before)
