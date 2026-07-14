import subprocess
from pathlib import Path
from typing import Final
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from pipx.util import PipxError
from pipx.venv import Venv


@pytest.fixture
def venv_with_site_packages(tmp_path: Path, mocker: MockerFixture) -> tuple[Venv, Path, MagicMock]:
    venv: Final[Venv] = Venv(tmp_path / "demo")
    venv.python_path.parent.mkdir(parents=True)
    venv.python_path.touch()
    site_packages: Final[Path] = tmp_path / "site-packages"
    dist_info: Final[Path] = site_packages / "demo-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text("Name: demo\nVersion: 1.0\n", encoding="utf-8")
    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.util.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{site_packages}\n", stderr=""),
    )
    return venv, dist_info, run_subprocess


def test_has_app_caches_site_packages(venv_with_site_packages: tuple[Venv, Path, MagicMock]) -> None:
    venv, dist_info, run_subprocess = venv_with_site_packages
    (dist_info / "entry_points.txt").write_text("[pipx.run]\ndemo = demo:main\n", encoding="utf-8")

    assert (venv.has_app("demo", "demo"), venv.has_app("demo", "demo")) == (True, True)
    run_subprocess.assert_called_once()


def test_run_app_rejects_python_args_without_entry_point(
    venv_with_site_packages: tuple[Venv, Path, MagicMock],
) -> None:
    venv, _, _ = venv_with_site_packages

    with pytest.raises(PipxError, match="'demo' is not a Python entry point"):
        venv.run_app("demo", "demo", [], python_args=["-b"])
