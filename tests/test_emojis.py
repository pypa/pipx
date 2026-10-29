from __future__ import annotations

import subprocess
import sys
from io import BytesIO, TextIOWrapper
from typing import TYPE_CHECKING

import pytest

from pipx.emojis import use_emojis

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "stderr_expression",
    [
        pytest.param("None", id="missing-stream"),
        pytest.param("io.StringIO()", id="missing-encoding"),
    ],
)
def test_import_without_stderr_encoding(stderr_expression: str) -> None:
    process = subprocess.run(
        [sys.executable, "-c", f"import io, sys; sys.stderr = {stderr_expression}; import pipx.emojis"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert process.returncode == 0, process.stderr


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        pytest.param({}, False, id="no-override"),
        pytest.param({"USE_EMOJI": "1"}, True, id="legacy-override"),
    ],
)
def test_use_emojis_without_stderr(
    no_emoji_override: pytest.MonkeyPatch, mocker: MockerFixture, environment: dict[str, str], expected: bool
) -> None:
    mocker.patch.object(sys, "stderr", None)
    for name, value in environment.items():
        no_emoji_override.setenv(name, value)

    assert use_emojis() is expected


@pytest.fixture
def no_emoji_override(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.delenv("PIPX_USE_EMOJI", raising=False)
    monkeypatch.delenv("USE_EMOJI", raising=False)
    return monkeypatch


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        pytest.param("utf-8", True, id="utf-8"),
        pytest.param("latin_1", False, id="latin-1"),
        pytest.param("cp1252", False, id="cp1252"),
    ],
)
@pytest.mark.usefixtures("no_emoji_override")
def test_use_emojis_follows_stderr_encoding(mocker: MockerFixture, encoding: str, expected: bool) -> None:
    mocker.patch.object(sys, "stderr", TextIOWrapper(BytesIO(), encoding=encoding))

    assert use_emojis() is expected


@pytest.mark.parametrize(
    "encoding",
    [
        pytest.param("utf-8", id="utf-8"),
        pytest.param("latin_1", id="latin-1"),
        pytest.param("cp1252", id="cp1252"),
    ],
)
@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param("", False, id="empty"),
        pytest.param("0", False, id="zero"),
        pytest.param("1", True, id="one"),
        pytest.param("true", True, id="true"),
        pytest.param("tru", False, id="misspelled"),  # codespell:ignore tru
        pytest.param("True", True, id="capitalized"),
        pytest.param("false", False, id="false"),
    ],
)
def test_use_emojis_override_ignores_stderr_encoding(
    no_emoji_override: pytest.MonkeyPatch,
    mocker: MockerFixture,
    encoding: str,
    env_value: str,
    expected: bool,
) -> None:
    mocker.patch.object(sys, "stderr", TextIOWrapper(BytesIO(), encoding=encoding))
    no_emoji_override.setenv("PIPX_USE_EMOJI", env_value)

    assert use_emojis() is expected
