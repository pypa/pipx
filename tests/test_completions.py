from pathlib import Path

import pytest

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
