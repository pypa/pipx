from __future__ import annotations

import locale
import os
import site
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

from pipx.util import read_pth_file, write_pth_file

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def non_ascii_dir() -> str:
    # only a name the locale encoding can represent encodes into a .pth file, and the OEM code page differs by system
    encoding: Final[str] = locale.getencoding()
    for name in ("用户", "àéîöü", "ユーザー", "пользователь", "사용자"):
        try:
            name.encode(encoding)
        except UnicodeEncodeError:
            continue
        return name
    pytest.skip(f"no non-ASCII directory name encodes in the {encoding} locale encoding")


@pytest.fixture
def source_env(root: Path) -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(root / "src")}


def test_pth_file_readable_with_non_ascii_path(tmp_path: Path, non_ascii_dir: str) -> None:
    non_ascii_path: Final[Path] = tmp_path / non_ascii_dir / "pipx" / "shared" / "site-packages"
    non_ascii_path.mkdir(parents=True)
    (tmp_path / "pipx_shared.pth").write_text(f"{non_ascii_path}\n")
    known_paths: Final[set[str]] = set()

    site.addpackage(str(tmp_path), "pipx_shared.pth", known_paths)

    assert str(non_ascii_path).casefold() in {path.casefold() for path in known_paths}


def test_pth_file_round_trip_in_utf8_mode(
    tmp_path: Path, non_ascii_dir: str, root: Path, source_env: dict[str, str]
) -> None:
    path: Final[Path] = tmp_path / "pipx_shared.pth"
    content: Final[str] = f"{tmp_path / non_ascii_dir / 'site-packages'}\n"
    code: Final[str] = (
        "import locale, sys\n"
        "from pathlib import Path\n"
        "from pipx.util import read_pth_file, write_pth_file\n"
        "path = Path(sys.argv[1])\n"
        "write_pth_file(path, sys.argv[2])\n"
        # Python 3.11 reads a .pth file only in the locale encoding, while 3.12+ falls back to it, so the bytes must
        # stay in it however the running interpreter handles UTF-8 mode
        "print(path.read_bytes() == sys.argv[2].encode(locale.getencoding()), read_pth_file(path) == sys.argv[2])\n"
    )

    # PEP 686 makes UTF-8 mode the default in Python 3.15, which changes what write_text() and read_text() use
    result: Final = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code, str(path), content],
        check=False,
        capture_output=True,
        cwd=root,
        env=source_env,
        text=True,
        errors="replace",  # the traceback of a failing run may carry bytes the locale cannot decode
    )

    assert (result.returncode, result.stdout) == (0, "True True\n"), result.stderr


@pytest.mark.parametrize(
    ("locale_encoding", "directory", "file_encoding"),
    [
        pytest.param("cp1252", "àéîöü", "cp1252", id="locale"),
        pytest.param("ascii", "用户", "utf-8", id="unencodable-fallback"),
    ],
)
def test_write_pth_file_uses_an_encoding_site_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, locale_encoding: str, directory: str, file_encoding: str
) -> None:
    monkeypatch.setattr(locale, "getencoding", lambda: locale_encoding)
    path: Final[Path] = tmp_path / "pipx_shared.pth"
    content: Final[str] = f"{tmp_path / directory / 'site-packages'}\n"

    write_pth_file(path, content)

    assert path.read_bytes() == content.encode(file_encoding)


def test_read_pth_file_falls_back_to_the_locale_encoding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252")
    path: Final[Path] = tmp_path / "pipx_shared.pth"
    content: Final[str] = f"{tmp_path / 'àéîöü' / 'site-packages'}\n"
    path.write_bytes(content.encode("cp1252"))

    assert read_pth_file(path) == content
