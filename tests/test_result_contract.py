from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final, TypeAlias, TypedDict

import pytest

from helpers import run_pipx_cli

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_JsonValue: TypeAlias = bool | int | float | str | list["_JsonValue"] | dict[str, "_JsonValue"] | None


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
    data: dict[str, _JsonValue]
    errors: list[_Error]


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_success_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    document: Final[_Envelope] = _envelope(capsys.readouterr().out)
    assert (document["command"], document["status"], document["exit_code"], document["errors"]) == (
        ["install"],
        "success",
        0,
        [],
    )


def _envelope(captured: str) -> _Envelope:
    document: Final[_Envelope] = json.loads(captured)
    assert (set(document), document["pipx_result_version"], isinstance(document["command"], list)) == (
        set(_Envelope.__annotations__),
        "1",
        True,
    )
    return document


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_error_envelope_names_the_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--app", "missing", "pycowsay"])

    document: Final[_Envelope] = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"], set(document["errors"][0]), document["errors"][0]["code"]) == (
        "error",
        1,
        set(_Error.__annotations__),
        "package_install_failed",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_contract_dispatch_error_uses_the_envelope(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    # a PipxError raised before a command returns a result must still speak JSON when the user selected --output json
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=False)

    assert run_pipx_cli(["reset", "--output", "json"])

    document: Final[_Envelope] = _envelope(capsys.readouterr().out)
    assert (document["status"], document["exit_code"], document["command"], document["errors"][0]["code"]) == (
        "error",
        1,
        ["reset"],
        "pipx_error",
    )
