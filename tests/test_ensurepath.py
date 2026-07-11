import os
import stat
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from helpers import run_pipx_cli
from pipx.commands import ensure_path as ensure_path_module
from pipx.constants import EXIT_CODE_OK, WINDOWS


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


@pytest.mark.parametrize(
    ("macos", "prepend", "expected"),
    [
        pytest.param(
            False,
            False,
            'case ":$PATH:" in *:/opt/pipx/bin:*) ;; *) export PATH="$PATH":/opt/pipx/bin ;; esac\n',
            id="linux-append",
        ),
        pytest.param(
            False,
            True,
            'case ":$PATH:" in *:/opt/pipx/bin:*) ;; *) export PATH=/opt/pipx/bin:"$PATH" ;; esac\n',
            id="linux-prepend",
        ),
        pytest.param(True, False, "/opt/pipx/bin\n", id="macos"),
    ],
)
def test_ensure_pipx_paths_global_updates_system_profile(
    mocker: MockerFixture, tmp_path: Path, macos: bool, prepend: bool, expected: str
) -> None:
    location = Path("/opt/pipx/bin")
    config_file = tmp_path / "etc/profile.d/pipx.sh"
    config_file.parent.mkdir(parents=True)
    mocker.patch.object(type(ensure_path_module.paths.ctx), "bin_dir", mocker.PropertyMock(return_value=location))
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", macos)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=prepend, is_global=True)

    assert config_file.read_text() == expected


def test_ensure_pipx_paths_global_skips_userpath(mocker: MockerFixture, tmp_path: Path) -> None:
    config_file = tmp_path / "pipx.sh"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    append = mocker.patch.object(ensure_path_module.userpath, "append", autospec=True)

    ensure_path_module.ensure_pipx_paths(force=False, is_global=True)

    append.assert_not_called()


def test_ensure_pipx_paths_global_dry_run_does_not_write(
    mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = tmp_path / "pipx.sh"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)

    ensure_path_module.ensure_pipx_paths(force=False, dry_run=True, is_global=True)

    assert not config_file.exists()
    assert "no changes were made to the system PATH" in capsys.readouterr().out


def test_ensure_pipx_paths_global_configuration_is_world_readable(mocker: MockerFixture, tmp_path: Path) -> None:
    config_file = tmp_path / "pipx"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    previous_umask = os.umask(0o077)
    try:
        ensure_path_module.ensure_pipx_paths(force=False, is_global=True)
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(config_file.stat().st_mode) == 0o644


def test_ensure_pipx_paths_global_reports_existing_configuration(
    mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    location = ensure_path_module.paths.ctx.bin_dir
    config_file = tmp_path / "pipx.sh"
    config_file.write_text(f"{location}\n")
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", True)

    ensure_path_module.ensure_pipx_paths(force=False, is_global=True)

    assert "already in the system PATH" in capsys.readouterr().out


@pytest.mark.skipif(WINDOWS, reason="The --global option is unavailable on Windows")
def test_ensurepath_cli_global_writes_system_configuration(
    mocker: MockerFixture, tmp_path: Path, pipx_temp_env: None
) -> None:
    config_file = tmp_path / "pipx"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)

    exit_code = run_pipx_cli(["ensurepath", "--global"])

    assert exit_code == EXIT_CODE_OK
    assert config_file.exists()
