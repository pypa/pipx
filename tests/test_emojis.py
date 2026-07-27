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


def test_use_emojis_without_stderr(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "stderr", None)
    monkeypatch.delenv("PIPX_USE_EMOJI", raising=False)
    monkeypatch.delenv("USE_EMOJI", raising=False)

    assert use_emojis() is False


def test_use_emojis_legacy_override_without_stderr(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "stderr", None)
    monkeypatch.delenv("PIPX_USE_EMOJI", raising=False)
    monkeypatch.setenv("USE_EMOJI", "1")

    assert use_emojis() is True


@pytest.mark.parametrize(
    ("env_value", "encoding", "expected"),
    [
        # utf-8
        (None, "utf-8", True),
        ("", "utf-8", False),
        ("0", "utf-8", False),
        ("1", "utf-8", True),
        ("true", "utf-8", True),
        ("tru", "utf-8", False),  # codespell:ignore tru
        ("True", "utf-8", True),
        ("false", "utf-8", False),
        # latin_1 (alias: iso-8859-1)
        (None, "latin_1", False),
        ("", "latin_1", False),
        ("0", "latin_1", False),
        ("1", "latin_1", True),
        ("true", "latin_1", True),
        ("tru", "latin_1", False),  # codespell:ignore tru
        ("True", "latin_1", True),
        ("false", "latin_1", False),
        # cp1252
        (None, "cp1252", False),
        ("", "cp1252", False),
        ("0", "cp1252", False),
        ("1", "cp1252", True),
        ("true", "cp1252", True),
        ("tru", "cp1252", False),  # codespell:ignore tru
        ("True", "cp1252", True),
        ("false", "cp1252", False),
    ],
)
def test_use_emojis(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    env_value: str | None,
    encoding: str,
    expected: bool,
) -> None:
    mocker.patch.object(sys, "stderr", TextIOWrapper(BytesIO(), encoding=encoding))
    monkeypatch.delenv("USE_EMOJI", raising=False)
    if env_value is None:
        monkeypatch.delenv("PIPX_USE_EMOJI", raising=False)
    else:
        monkeypatch.setenv("PIPX_USE_EMOJI", env_value)

    assert use_emojis() is expected
