from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from helpers import run_pipx_cli
from pipx import main
from pipx.venv import VenvContainer


def test_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["completions"])
    captured = capsys.readouterr()
    assert "Add the appropriate command" in captured.out


def test_installed_venvs_noncanonical_prefix(tmp_path: Path) -> None:
    (tmp_path / "my-pkg").mkdir()
    completer = main.InstalledVenvsCompleter(VenvContainer(tmp_path))

    assert completer.use("my__p") == ["my__pkg"]


def test_installed_venvs_defers_listing(tmp_path: Path, mocker: MockerFixture) -> None:
    venv_container = VenvContainer(tmp_path)
    iter_venv_dirs = mocker.spy(venv_container, "iter_venv_dirs")
    completer = main.InstalledVenvsCompleter(venv_container)

    iter_venv_dirs.assert_not_called()
    assert (completer.use(""), completer.use("")) == ([], [])
    iter_venv_dirs.assert_called_once_with()
