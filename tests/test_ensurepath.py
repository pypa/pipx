from pathlib import Path

import pytest

from pipx.commands import ensure_path as ensure_path_module
from pipx.constants import EXIT_CODE_OK


class FakeUserpath:
    """Minimal stand-in for the ``userpath`` module used by ensure_path.

    Records append/prepend calls so tests can assert that a dry run never
    mutates PATH or any shell configuration file.
    """

    def __init__(self) -> None:
        self.append_calls: list[str] = []
        self.prepend_calls: list[str] = []
        self.in_path = False
        self.restart = False

    def need_shell_restart(self, location: str) -> bool:
        return self.restart

    def in_current_path(self, location: str) -> bool:
        return self.in_path

    def append(self, location: str, app: str, all_shells: bool = False) -> bool:
        self.append_calls.append(location)
        return True

    def prepend(self, location: str, app: str, all_shells: bool = False) -> bool:
        self.prepend_calls.append(location)
        return True


@pytest.fixture
def mock_userpath(monkeypatch: pytest.MonkeyPatch) -> FakeUserpath:
    fake = FakeUserpath()
    monkeypatch.setattr(ensure_path_module, "userpath", fake)
    return fake


def test_ensure_path_dry_run_does_not_append(mock_userpath: FakeUserpath, capsys: pytest.CaptureFixture[str]) -> None:
    location = Path("/some/bin")
    path_added, _ = ensure_path_module.ensure_path(location, force=True, dry_run=True)

    assert path_added is False
    assert mock_userpath.append_calls == []
    assert mock_userpath.prepend_calls == []
    assert "Would append" in capsys.readouterr().out


def test_ensure_path_dry_run_reports_prepend(mock_userpath: FakeUserpath, capsys: pytest.CaptureFixture[str]) -> None:
    location = Path("/some/bin")
    ensure_path_module.ensure_path(location, force=True, prepend=True, dry_run=True)

    assert mock_userpath.prepend_calls == []
    assert "Would prepend" in capsys.readouterr().out


def test_ensure_path_non_dry_run_still_appends(mock_userpath: FakeUserpath, capsys: pytest.CaptureFixture[str]) -> None:
    location = Path("/some/bin")
    ensure_path_module.ensure_path(location, force=True)

    assert mock_userpath.append_calls == [str(location)]
    assert "Success!" in capsys.readouterr().out


def test_ensure_pipx_paths_dry_run_footer(mock_userpath: FakeUserpath, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = ensure_path_module.ensure_pipx_paths(force=True, dry_run=True)

    assert exit_code == EXIT_CODE_OK
    assert mock_userpath.append_calls == []
    out = capsys.readouterr().out.lower()
    assert "dry run" in out
    assert "no changes were made" in out
