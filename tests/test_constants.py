import sys
from io import BytesIO, TextIOWrapper

import pytest  # type: ignore

from pipx.constants import use_emjois


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
        # latin-1
        (None, "latin-1", False),
        ("", "latin-1", False),
        ("0", "latin-1", False),
        ("1", "latin-1", True),
        ("true", "latin-1", True),
        ("tru", "latin-1", False),
        ("True", "latin-1", True),
        ("false", "latin-1", False),
        # iso8859-1
        (None, "iso8859-1", False),
        ("", "iso8859-1", False),
        ("0", "iso8859-1", False),
        ("1", "iso8859-1", True),
        ("true", "iso8859-1", True),
        ("tru", "iso8859-1", False),
        ("True", "iso8859-1", True),
        ("false", "iso8859-1", False),
    ],
)
def test_use_emjois(monkeypatch, USE_EMOJI, encoding, expected):
    sys.stderr = TextIOWrapper(BytesIO(), encoding=encoding)
    if USE_EMOJI is not None:
        monkeypatch.setenv("USE_EMOJI", USE_EMOJI)
    assert use_emjois() is expected
