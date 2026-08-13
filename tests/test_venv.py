from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture
def venv_with_site_packages(tmp_path: Path, mocker: MockerFixture) -> tuple[Venv, tuple[Path, Path], MagicMock]:
    venv: Final[Venv] = Venv(tmp_path / "demo")
    venv.python_path.parent.mkdir(parents=True)
    venv.python_path.touch()
    purelib: Final[Path] = venv.root / "lib" / "site-packages"
    platlib: Final[Path] = venv.root / "lib64" / "site-packages"

    purelib_demo: Final[Path] = purelib / "demo-1.0.dist-info"
    purelib_demo.mkdir(parents=True)
    (purelib_demo / "METADATA").write_text("Name: demo\nVersion: 1.0\n", encoding="utf-8")

    platlib_demo: Final[Path] = platlib / "demo2-1.0.dist-info"
    platlib_demo.mkdir(parents=True)
    (platlib_demo / "METADATA").write_text("Name: demo2\nVersion: 1.0\n", encoding="utf-8")

    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.util.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{purelib}\n{platlib}\n", stderr=""),
    )
    return venv, (purelib_demo, platlib_demo), run_subprocess


def test_has_package(venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock]) -> None:
    venv, _, _ = venv_with_site_packages
    assert (venv.has_package("demo"), venv.has_package("demo2")) == (True, True)


def test_has_app_caches_site_packages(venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock]) -> None:
    venv, (purelib_demo, _), run_subprocess = venv_with_site_packages
    (purelib_demo / "entry_points.txt").write_text("[pipx.run]\ndemo = demo:main\n", encoding="utf-8")

    assert (venv.has_app("demo", "demo"), venv.has_app("demo", "demo")) == (True, True)
    run_subprocess.assert_called_once()


def test_run_app_rejects_python_args_without_entry_point(
    venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock],
) -> None:
    venv, _, _ = venv_with_site_packages

    with pytest.raises(PipxError, match="'demo' is not a Python entry point"):
        venv.run_app("demo", "demo", [], python_args=["-b"])
