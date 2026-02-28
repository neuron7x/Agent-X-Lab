from __future__ import annotations

import hashlib
import json
import os
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


def _git_head_available() -> bool:
    import subprocess

    p = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return p.returncode == 0


@pytest.fixture(autouse=True)
def ensure_build_id_without_git() -> None:
    if os.environ.get("BUILD_ID", "").strip():
        return
    if _git_head_available():
        return
    os.environ["BUILD_ID"] = "test-ci-stub-session"


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



@pytest.fixture(autouse=True)
def enforce_hermetic_artifact_roots(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if "test_isolation_fixture.py" in request.node.nodeid:
        return
    root = tmp_path_factory.mktemp("axl-hermetic")
    monkeypatch.setenv("AXL_TEST_OUTPUT_DIR", str((root / "test-output").resolve()))
    monkeypatch.setenv("AXL_ARTIFACTS_ROOT", str((root / "artifacts").resolve()))
