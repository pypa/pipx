from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from pipx.script import ScriptMetadata, installable_script, read_script_metadata, script_name_from_spec
from pipx.util import PipxError

if TYPE_CHECKING:
    from pathlib import Path


def test_read_script_metadata() -> None:
    metadata: Final[ScriptMetadata | None] = read_script_metadata(
        """# /// script
# dependencies = ["requests >= 2"]
# requires-python = ">=3.10"
# ///
"""
    )

    assert metadata == ScriptMetadata(("requests>=2",), ">=3.10")


def test_read_script_metadata_path(tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "app.py"
    script.write_text("# /// script\n# dependencies = []\n# ///\n", encoding="utf-8-sig", newline="\r\n")

    assert read_script_metadata(script) == ScriptMetadata((), None)


def test_read_script_metadata_missing() -> None:
    assert read_script_metadata("print('hello')\n") is None


@pytest.mark.parametrize(
    ("content", "message", "error_type"),
    [
        (
            "# /// script\n# dependencies = [1]\n# ///\n",
            "dependencies.*array of strings",
            PipxError,
        ),
        (
            '# /// script\n# dependencies = ["???"]\n# ///\n',
            "Invalid requirement",
            PipxError,
        ),
        (
            "# /// script\n# dependencies = []\n# requires-python = []\n# ///\n",
            "requires-python.*string",
            PipxError,
        ),
        (
            '# /// script\n# dependencies = []\n# requires-python = "invalid"\n# ///\n',
            "Invalid.*requires-python",
            PipxError,
        ),
        (
            "# /// pyproject\n# dependencies = []\n# ///\n",
            "obsolete.*pyproject",
            ValueError,
        ),
        (
            "# /// script\n# dependencies = []\n# ///\n# /// script\n# dependencies = []\n# ///\n",
            "Multiple",
            ValueError,
        ),
    ],
    ids=("dependencies", "requirement", "requires-python-type", "requires-python-value", "obsolete", "multiple"),
)
def test_read_script_metadata_invalid(content: str, message: str, error_type: type[Exception]) -> None:
    with pytest.raises(error_type, match=message):
        read_script_metadata(content)


@pytest.mark.parametrize(
    ("spec", "expected_apps", "name"),
    [
        ("https://example.invalid/My_App.py", (), "my-app"),
        ("https://example.invalid/app.py?version=1", ("Other_App",), "other-app"),
        ("https://example.invalid/app.whl", (), None),
    ],
    ids=("url", "override", "package"),
)
def test_script_name_from_spec(spec: str, expected_apps: tuple[str, ...], name: str | None) -> None:
    assert script_name_from_spec(spec, expected_apps) == name


def test_script_name_from_spec_path(tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "My_App.py"
    script.touch()

    assert script_name_from_spec(str(script), ()) == "my-app"


def test_script_name_from_spec_path_without_suffix(tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "My_App"
    script.write_text("# /// script\n# dependencies = []\n# ///\n", encoding="utf-8")

    assert script_name_from_spec(str(script), ()) == "my-app"


def test_script_name_from_spec_binary_without_suffix(tmp_path: Path) -> None:
    binary: Final[Path] = tmp_path / "binary"
    binary.write_bytes(b"\xff\xfe")

    assert script_name_from_spec(str(binary), ()) is None


def test_installable_script_rejects_name_mismatch() -> None:
    with pytest.raises(PipxError, match="does not match"):
        with installable_script("other", "https://example.invalid/app.py", ()):
            pass


@pytest.mark.parametrize(
    ("expected_apps", "message"),
    [
        (("first", "second"), "one --app"),
        (("bad/app",), "portable command name"),
    ],
    ids=("multiple", "invalid"),
)
def test_script_name_from_spec_invalid(expected_apps: tuple[str, ...], message: str) -> None:
    with pytest.raises(PipxError, match=message):
        script_name_from_spec("https://example.invalid/app.py", expected_apps)
