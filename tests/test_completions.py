from __future__ import annotations

from typing import TYPE_CHECKING, Final

from helpers import run_pipx_cli
from pipx.main import InstalledVenvsCompleter
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    import pytest
    from pytest_mock import MockerFixture


def test_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["completions"])
    assert "Add the command for your shell" in capsys.readouterr().out


def test_installed_venvs_noncanonical_prefix(tmp_path: Path) -> None:
    (tmp_path / "my-pkg").mkdir()

    assert InstalledVenvsCompleter(VenvContainer(tmp_path)).use("my__p") == ["my__pkg"]


def test_installed_venvs_defers_listing(tmp_path: Path, mocker: MockerFixture) -> None:
    venv_container: Final[VenvContainer] = VenvContainer(tmp_path)
    iter_venv_dirs: Final[MagicMock] = mocker.spy(venv_container, "iter_venv_dirs")
    completer: Final[InstalledVenvsCompleter] = InstalledVenvsCompleter(venv_container)

    iter_venv_dirs.assert_not_called()
    assert (completer.use(""), completer.use("")) == ([], [])
    iter_venv_dirs.assert_called_once_with()
