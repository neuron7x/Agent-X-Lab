from __future__ import annotations

import os
import sys
import types


_LEAK_MODULE_NAME = "exoneural_governor._isolation_leak_probe"
_LEAK_MODULE_NAME_SCRIPTS = "scripts._isolation_leak_probe"
_LEAK_ENV_KEY = "AGENTX_ISOLATION_LEAK"
_BASE_ENV = dict(os.environ)


def _stable_environ_snapshot() -> dict[str, str]:
    snapshot = dict(os.environ)
    snapshot.pop("PYTEST_CURRENT_TEST", None)
    return snapshot


def test_isolation_creates_temporary_module_and_env_changes() -> None:
    sys.modules[_LEAK_MODULE_NAME] = types.ModuleType(_LEAK_MODULE_NAME)
    sys.modules[_LEAK_MODULE_NAME_SCRIPTS] = types.ModuleType(_LEAK_MODULE_NAME_SCRIPTS)

    os.environ[_LEAK_ENV_KEY] = "set-during-test"

    assert _LEAK_MODULE_NAME in sys.modules
    assert _LEAK_MODULE_NAME_SCRIPTS in sys.modules
    assert os.environ[_LEAK_ENV_KEY] == "set-during-test"


def test_isolation_removes_product_module_leaks_and_restores_environment() -> None:
    assert _LEAK_MODULE_NAME not in sys.modules
    assert _LEAK_MODULE_NAME_SCRIPTS not in sys.modules
    assert _LEAK_ENV_KEY not in os.environ
    assert _stable_environ_snapshot() == {
        k: v for k, v in _BASE_ENV.items() if k != "PYTEST_CURRENT_TEST"
    }


def test_environment_parity_restores_removed_or_modified_keys() -> None:
    for key in list(os.environ):
        if key in {"PATH", "HOME"}:
            os.environ.pop(key, None)
    os.environ["PATH"] = "temporary-path-value"
    os.environ["HOME"] = "temporary-home-value"
    os.environ["AGENTX_PARITY_EXTRA"] = "extra"

    assert os.environ["PATH"] == "temporary-path-value"


def test_environment_parity_is_strict_after_mutation() -> None:
    assert _stable_environ_snapshot() == {
        k: v for k, v in _BASE_ENV.items() if k != "PYTEST_CURRENT_TEST"
    }
