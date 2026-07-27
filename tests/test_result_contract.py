from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final, TypedDict

import pytest

from helpers import run_pipx_cli

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class _Error(TypedDict):
    code: str
    message: str
    environment: str | None
    package: str | None


class _Envelope(TypedDict):
    pipx_result_version: str
    command: list[str]
    status: str
    exit_code: int
    data: dict[str, object]
    errors: list[_Error]


_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(_Envelope.__annotations__)
_ERROR_KEYS: Final[frozenset[str]] = frozenset(_Error.__annotations__)


def _envelope(captured: str) -> _Envelope:
    document: _Envelope = json.loads(captured)
    assert set(document) == _ENVELOPE_KEYS
    assert document["pipx_result_version"] == "1"
    assert isinstance(document["command"], list)
    return document


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_success_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    document = _envelope(capsys.readouterr().out)
    assert (document["command"], document["status"], document["exit_code"], document["errors"]) == (
        ["install"],
        "success",
        0,
        [],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_error_envelope_names_the_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--app", "missing", "pycowsay"])

    document = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"]) == ("error", 1)
    assert set(document["errors"][0]) == _ERROR_KEYS
    assert document["errors"][0]["code"] == "package_install_failed"


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_dispatch_error_uses_the_envelope(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    # a PipxError raised before a command returns a result must still speak JSON when --output json was selected
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=False)

    assert run_pipx_cli(["reset", "--output", "json"])

    document = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"], document["command"]) == ("error", 1, ["reset"])
    assert document["errors"][0]["code"] == "pipx_error"
