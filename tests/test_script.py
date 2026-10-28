from __future__ import annotations

from typing import TYPE_CHECKING, Final
from urllib.error import URLError
from zipfile import ZipFile

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx.script import (
    _MAX_SCRIPT_BYTES,  # ruff:ignore[import-private-name]  # test exercises private helper, no public API
    ScriptMetadata,
    _read_url,  # ruff:ignore[import-private-name]  # test exercises private helper, no public API
    installable_script,
    local_script,
    read_script_metadata,
    script_name_from_spec,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


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


@pytest.mark.parametrize(
    ("quote", "line"),
    [
        pytest.param('"""', "# ///", id="basic-string-closing"),
        pytest.param("'''", "# ///", id="literal-string-closing"),
        pytest.param('"""', "# /// other", id="basic-string-header"),
    ],
)
def test_read_script_metadata_delimiter_in_multiline_string(quote: str, line: str) -> None:
    content: Final[str] = (
        f'# /// script\n# dependencies = ["demo"]\n# [tool.demo]\n# text = {quote}\n{line}\n# {quote}\n# ///\n'
    )

    assert read_script_metadata(content) == ScriptMetadata(("demo",), None)


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
            "# /// script\n# dependencies = []\n# ///\n\n# /// script\n# dependencies = []\n# ///\n",
            "Multiple",
            ValueError,
        ),
        (
            "# /// script\n# dependencies = []\n# ///\n# /// script\n# dependencies = []\n# ///\n",
            "Invalid statement",
            ValueError,
        ),
    ],
    ids=(
        "dependencies",
        "requirement",
        "requires-python-type",
        "requires-python-value",
        "obsolete",
        "multiple",
        "adjacent",
    ),
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


@pytest.mark.parametrize("filename", [pytest.param("My_App.py", id="suffix"), pytest.param("My_App", id="no-suffix")])
@pytest.mark.parametrize(
    "directory",
    [
        pytest.param("scripts", id="plain"),
        pytest.param("scripts#123", id="hash"),
        pytest.param("Project #123", id="space-and-hash"),
    ],
)
def test_script_name_from_spec_path(tmp_path: Path, directory: str, filename: str) -> None:
    (script_dir := tmp_path / directory).mkdir()
    (script := script_dir / filename).write_text("# /// script\n# dependencies = []\n# ///\n", encoding="utf-8")

    assert script_name_from_spec(str(script), ()) == "my-app"


def test_script_name_from_spec_binary_without_suffix(tmp_path: Path) -> None:
    binary: Final[Path] = tmp_path / "binary"
    binary.write_bytes(b"\xff\xfe")

    assert script_name_from_spec(str(binary), ()) is None


@pytest.mark.parametrize(
    ("spec", "name"),
    [
        pytest.param("my_app", None, id="bare-name"),
        pytest.param("./my_app", "my-app", id="relative-path"),
    ],
)
def test_script_name_from_spec_without_suffix_needs_a_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spec: str, name: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my_app").write_text("# /// script\n# dependencies = []\n# ///\n", encoding="utf-8")

    assert script_name_from_spec(spec, ()) == name


@skip_if_windows
@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://example.invalid/app.py", id="py-suffix"),
        pytest.param("https://example.invalid/app", id="no-suffix"),
        pytest.param("file:///srv/app.py", id="file-url"),
    ],
)
def test_local_script_ignores_file_below_cwd_named_like_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.chdir(tmp_path)
    (lookalike := tmp_path / url).parent.mkdir(parents=True)
    lookalike.write_text("# /// script\n# dependencies = []\n# ///\n", encoding="utf-8")

    assert local_script(url) is None


@skip_if_windows
def test_installable_script_downloads_url_over_file_below_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.chdir(tmp_path)
    url: Final[str] = "https://example.invalid/app.py"
    (lookalike := tmp_path / url).parent.mkdir(parents=True)
    lookalike.write_text("# /// script\n# dependencies = []\n# ///\nprint('local')\n", encoding="utf-8")
    remote: Final[str] = "# /// script\n# dependencies = []\n# ///\nprint('remote')\n"
    response = mocker.MagicMock(**{
        "read.return_value": remote.encode(),
        "headers.get_content_charset.return_value": "utf-8",
    })
    response.__enter__.return_value = response
    mocker.patch("urllib.request.urlopen", return_value=response)

    with installable_script("app", url, ()) as wheel, ZipFile(wheel) as archive:
        assert archive.read("_pipx_script_app/_script.py").decode() == remote


def test_installable_script_rejects_name_mismatch() -> None:
    with (
        pytest.raises(PipxError, match="does not match"),
        installable_script("other", "https://example.invalid/app.py", ()),
    ):
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


def test_read_url_bounds_the_response_size(mocker: MockerFixture) -> None:
    response = mocker.MagicMock()
    response.read.return_value = b"x" * (_MAX_SCRIPT_BYTES + 1)
    response.headers.get_content_charset.return_value = "utf-8"
    response.__enter__.return_value = response
    urlopen = mocker.patch("urllib.request.urlopen", return_value=response)

    with pytest.raises(PipxError, match="larger than"):
        _read_url("https://example.invalid/big.py")
    assert urlopen.call_args.kwargs["timeout"] == 30


@pytest.mark.parametrize(
    ("userinfo", "masked"),
    [pytest.param("alice:s3cr3t@", "alice:****@", id="password"), pytest.param("t0ken@", "****@", id="token")],
)
@pytest.mark.parametrize("command", [pytest.param("install", id="install"), pytest.param("run", id="run")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_script_url_with_credentials_is_rejected_masked(
    capsys: pytest.CaptureFixture[str], command: str, userinfo: str, masked: str
) -> None:
    assert run_pipx_cli([command, f"https://{userinfo}localhost/tool.py"]) == 1

    assert f"Script URL https://{masked}localhost/tool.py must not contain credentials." in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_script_url_with_invalid_port_reports_url(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "https://localhost:port/tool.py"]) == 1

    assert "Unable to read script https://localhost:port/tool.py: nonnumeric port: 'port'" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_ftp_script_url_passes_credentials_to_urllib(mocker: MockerFixture) -> None:
    urlopen = mocker.patch("urllib.request.urlopen", side_effect=URLError("refused"))

    assert run_pipx_cli(["run", "ftp://alice:s3cr3t@localhost/tool.py"]) == 1

    assert urlopen.call_args.args[0] == "ftp://alice:s3cr3t@localhost/tool.py"
