from __future__ import annotations

import locale
import site
from typing import TYPE_CHECKING, Final

import pytest

from pipx.constants import PIPX_SHARED_PTH
from pipx.shared_libs import SHARED_LIBS, write_shared_pth
from pipx.util import read_pth_file

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


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


def test_pth_file_readable_with_non_ascii_path(tmp_path: Path, non_ascii_dir: str) -> None:
    non_ascii_path: Final[Path] = tmp_path / non_ascii_dir / "pipx" / "shared" / "site-packages"
    non_ascii_path.mkdir(parents=True)
    (tmp_path / "pipx_shared.pth").write_text(f"{non_ascii_path}\n")
    known_paths: Final[set[str]] = set()

    site.addpackage(str(tmp_path), "pipx_shared.pth", known_paths)

    assert str(non_ascii_path).casefold() in {path.casefold() for path in known_paths}


@pytest.mark.parametrize(
    ("pyvenv_cfg", "pythonutf8", "expected"),
    [
        pytest.param("version = 3.13.1\n", "0", "utf-8", id="3.13-reads-utf-8-first"),
        pytest.param("version = 3.12.4\n", "0", "utf-8", id="3.12.4-reads-utf-8-first"),
        pytest.param("version = 3.12.3\n", "0", "cp1252", id="3.12.3-reads-only-the-locale-encoding"),
        pytest.param("version = 3.11.9\n", "1", "cp1252", id="3.11-ignores-utf-8-mode"),
        pytest.param("version_info = 3.11\n", "0", "cp1252", id="3.11-created-by-uv"),
        pytest.param("version = 3.10.16\n", "0", "cp1252", id="3.10-reads-the-locale-encoding"),
        pytest.param("version = 3.10.16\n", "1", "utf-8", id="3.10-in-utf-8-mode"),
        pytest.param("", "0", "utf-8", id="unknown-version"),
    ],
)
def test_write_shared_pth_uses_the_encoding_the_environment_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pyvenv_cfg: str, pythonutf8: str, expected: str
) -> None:
    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252")
    monkeypatch.setenv("PYTHONUTF8", pythonutf8)
    shared: Final[Path] = tmp_path / "àéîöü" / "site-packages"
    monkeypatch.setattr(type(SHARED_LIBS), "site_packages", property(lambda _: [shared]))
    (tmp_path / "pyvenv.cfg").write_text(pyvenv_cfg, encoding="utf-8")

    write_shared_pth(tmp_path, tmp_path)

    assert (tmp_path / PIPX_SHARED_PTH).read_bytes() == f"{shared}\n".encode(expected)


def test_write_shared_pth_repairs_a_file_in_the_wrong_encoding(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(locale, "getencoding", autospec=True, return_value="cp1252")
    shared: Final[Path] = tmp_path / "àéîöü" / "site-packages"
    mocker.patch.object(type(SHARED_LIBS), "site_packages", new_callable=mocker.PropertyMock, return_value=[shared])
    (tmp_path / "pyvenv.cfg").write_text("version = 3.11.9\n", encoding="utf-8")
    (pth := tmp_path / PIPX_SHARED_PTH).write_bytes(f"{shared}\n".encode())

    write_shared_pth(tmp_path, tmp_path)

    assert pth.read_bytes() == f"{shared}\n".encode("cp1252")


def test_read_pth_file_falls_back_to_the_locale_encoding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252")
    path: Final[Path] = tmp_path / "pipx_shared.pth"
    content: Final[str] = f"{tmp_path / 'àéîöü' / 'site-packages'}\n"
    path.write_bytes(content.encode("cp1252"))

    assert read_pth_file(path) == content
