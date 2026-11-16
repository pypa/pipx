from __future__ import annotations

import locale
import os
import site
import sys
from typing import TYPE_CHECKING, Final
from venv import EnvBuilder

import pytest

from harness import WIN
from pipx.constants import PIPX_SHARED_PTH
from pipx.shared_libs import SHARED_LIBS
from pipx.util import read_pth_file, write_pth_file
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "non_ascii_dir",
    [
        pytest.param("用户", id="posix", marks=pytest.mark.skipif(WIN, reason="the Windows case uses Latin letters")),
        pytest.param("àéîöü", id="windows", marks=pytest.mark.skipif(not WIN, reason="Windows only")),
    ],
)
def test_pth_file_readable_with_non_ascii_path(tmp_path: Path, non_ascii_dir: str) -> None:
    non_ascii_path: Final[Path] = tmp_path / non_ascii_dir / "pipx" / "shared" / "site-packages"
    non_ascii_path.mkdir(parents=True)
    (tmp_path / "pipx_shared.pth").write_text(f"{non_ascii_path}\n")
    known_paths: Final[set[str]] = set()

    site.addpackage(str(tmp_path), "pipx_shared.pth", known_paths)

    assert str(non_ascii_path).casefold() in {path.casefold() for path in known_paths}


@pytest.fixture
def shared_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    # Simulate a Windows ANSI locale even on UTF-8-only CI hosts. File I/O remains real.
    monkeypatch.setattr(locale, "getencoding", lambda: "cp936")
    paths: Final[list[Path]] = [tmp_path / "测试 目录" / name for name in ("purelib", "platlib")]
    for path in paths:
        (path / "demo-1.0.dist-info").mkdir(parents=True)
    monkeypatch.setattr(type(SHARED_LIBS), "site_packages", property(lambda _self: paths))
    monkeypatch.setattr(type(SHARED_LIBS), "is_valid", property(lambda _self: True))
    # Shared pip provisioning is independent of the .pth file in the application environment.
    monkeypatch.setattr(SHARED_LIBS, "create", lambda **_kwargs: None)
    return paths


def test_create_venv_pth_uses_locale_encoding(tmp_path: Path, shared_paths: list[Path]) -> None:
    venv: Final[Venv] = Venv(tmp_path / "venv", python=sys.executable)
    venv.create_venv([], [])
    pth: Final[Path] = venv.site_packages[0] / PIPX_SHARED_PTH

    assert pth.read_bytes() == "".join(f"{path}\n" for path in shared_paths).replace("\n", os.linesep).encode("cp936")


@pytest.fixture(params=["cp936", "utf-8"])
def existing_pth_venv(tmp_path: Path, shared_paths: list[Path], request: pytest.FixtureRequest) -> Venv:
    venv: Final[Venv] = Venv(tmp_path / "venv", python=sys.executable)
    EnvBuilder(with_pip=False).create(venv.root)
    pth: Final[Path] = venv.site_packages[0] / PIPX_SHARED_PTH
    pth.write_text("".join(f"{path}\n" for path in shared_paths), encoding=request.param)
    return venv


def test_existing_pth_encoding_for_installer(existing_pth_venv: Venv) -> None:
    assert existing_pth_venv._installer_python == existing_pth_venv.python_path  # ruff:ignore[private-member-access]  # exercise pth repair


def test_existing_pth_encoding_for_distributions(existing_pth_venv: Venv) -> None:
    assert existing_pth_venv._installed_distribution_names() == {"demo"}  # ruff:ignore[private-member-access]  # pth consumer


def test_write_pth_falls_back_when_locale_cannot_encode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locale, "getencoding", lambda: "cp936")
    pth: Final[Path] = tmp_path / "pipx_shared.pth"
    contents: Final[str] = "C:/Users/😀/pipx/shared\n"

    write_pth_file(pth, contents)

    assert pth.read_bytes() == contents.replace("\n", os.linesep).encode("utf-8")
    assert read_pth_file(pth) == contents


def test_repair_pth_uses_locale_encoding(tmp_path: Path, shared_paths: list[Path]) -> None:
    venv: Final[Venv] = Venv(tmp_path / "venv", python=sys.executable)
    EnvBuilder(with_pip=False).create(venv.root)
    pth: Final[Path] = venv.site_packages[0] / PIPX_SHARED_PTH
    pth.write_text("old/shared/site-packages\n", encoding="ascii")

    assert venv._installer_python == venv.python_path  # ruff:ignore[private-member-access]  # exercise pth repair
    assert pth.read_text(encoding="cp936").splitlines() == [str(path) for path in shared_paths]
