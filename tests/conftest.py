from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator

import pytest

PRODUCT_MODULE_PREFIXES = (
    "exoneural_governor",
    "scripts",
)


def _canonical_env_hash(env: dict[str, str]) -> str:
    payload = json.dumps(sorted(env.items()), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture(autouse=True)
def isolate_runtime_state() -> Iterator[None]:
    modules_before = set(sys.modules.keys())
    environ_before = dict(os.environ)
    environ_before_hash = _canonical_env_hash(environ_before)

    yield

    post_modules = set(sys.modules.keys())
    new_modules = post_modules - modules_before
    for module_name in new_modules:
        if module_name.startswith(PRODUCT_MODULE_PREFIXES):
            sys.modules.pop(module_name, None)

    post_env = dict(os.environ)
    for key in list(post_env.keys()):
        if key not in environ_before:
            os.environ.pop(key, None)
    for key, value in environ_before.items():
        os.environ[key] = value

    assert _canonical_env_hash(dict(os.environ)) == environ_before_hash


@pytest.fixture(autouse=True, scope="session")
def ensure_build_id() -> None:
    if os.environ.get("BUILD_ID"):
        return
    if subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True).returncode != 0:
        os.environ["BUILD_ID"] = "test-ci-stub-session"
