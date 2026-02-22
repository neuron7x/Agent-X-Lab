from __future__ import annotations

from pathlib import Path

import pytest

from exoneural_governor import cli


def test_cli_malformed_subcommand_fails_closed() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["not-a-real-command"])

    assert exc.value.code == 2


def test_cli_timeout_from_dependency_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_timeout(*_args, **_kwargs):
        raise TimeoutError("dependency timed out")

    monkeypatch.setattr(cli, "validate_catalog", _raise_timeout)

    with pytest.raises(TimeoutError, match="dependency timed out"):
        cli.cmd_selftest(Path("configs/sg.config.json"))


def test_cli_dependency_failure_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_io(*_args, **_kwargs):
        raise OSError("catalog backend unavailable")

    monkeypatch.setattr(cli, "validate_catalog", _raise_io)

    with pytest.raises(OSError, match="catalog backend unavailable"):
        cli.cmd_validate(Path("configs/sg.config.json"))
