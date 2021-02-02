import sys
from io import BytesIO, TextIOWrapper
from unittest import mock

import pytest  # type: ignore

from pipx.emojis import use_emojis


@pytest.mark.parametrize(
    "USE_EMOJI, encoding, expected",
    [
        # utf-8
        (None, "utf-8", True),
        ("", "utf-8", False),
        ("0", "utf-8", False),
        ("1", "utf-8", True),
        ("true", "utf-8", True),
        ("tru", "utf-8", False),
        ("True", "utf-8", True),
        ("false", "utf-8", False),
        # latin_1 (alias: iso-8859-1)
        (None, "latin_1", False),
        ("", "latin_1", False),
        ("0", "latin_1", False),
        ("1", "latin_1", True),
        ("true", "latin_1", True),
        ("tru", "latin_1", False),
        ("True", "latin_1", True),
        ("false", "latin_1", False),
        # cp1252
        (None, "cp1252", False),
        ("", "cp1252", False),
        ("0", "cp1252", False),
        ("1", "cp1252", True),
        ("true", "cp1252", True),
        ("tru", "cp1252", False),
        ("True", "cp1252", True),
        ("false", "cp1252", False),
    ],
)
def test_use_emojis(monkeypatch, USE_EMOJI, encoding, expected):
    with mock.patch.object(sys, "stderr", TextIOWrapper(BytesIO(), encoding=encoding)):
        if USE_EMOJI is not None:
            monkeypatch.setenv("USE_EMOJI", USE_EMOJI)
        assert use_emojis() is expected
