from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from helpers import run_pipx_cli

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pytest
    from pytest_mock import MockerFixture

_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(
    {"pipx_result_version", "command", "status", "exit_code", "data", "errors"}
)
_ERROR_KEYS: Final[frozenset[str]] = frozenset({"code", "message", "environment", "package"})


def _envelope(captured: str) -> Mapping[str, object]:
    document = json.loads(captured)
    assert set(document) == _ENVELOPE_KEYS
    assert document["pipx_result_version"] == "1"
    assert isinstance(document["command"], list)
    return document


def test_contract_success_envelope(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    document = _envelope(capsys.readouterr().out)
    assert (document["command"], document["status"], document["exit_code"], document["errors"]) == (
        ["install"],
        "success",
        0,
        [],
    )


def test_contract_error_envelope_names_the_failure(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--app", "missing", "pycowsay"])

    document = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"]) == ("error", 1)
    assert set(document["errors"][0]) == _ERROR_KEYS  # type: ignore[index]
    assert document["errors"][0]["code"] == "package_install_failed"  # type: ignore[index]


def test_contract_dispatch_error_uses_the_envelope(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    # a PipxError raised before a command returns a result must still speak JSON when --output json was selected
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=False)

    assert run_pipx_cli(["reset", "--output", "json"])

    document = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"], document["command"]) == ("error", 1, ["reset"])
    assert document["errors"][0]["code"] == "pipx_error"  # type: ignore[index]
