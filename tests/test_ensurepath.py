from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
import userpath

from helpers import run_pipx_cli
from pipx import paths
from pipx.commands import ensure_path as ensure_path_module
from pipx.constants import EXIT_CODE_OK, WINDOWS

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

_SKIP_GLOBAL_ON_WINDOWS: Final = pytest.mark.skipif(WINDOWS, reason="System-wide ensurepath is unavailable on Windows")


@pytest.fixture
def mock_userpath(mocker: MockerFixture) -> MagicMock:
    mocked: Final = mocker.create_autospec(
        userpath,
        **{
            "need_shell_restart.return_value": False,
            "in_current_path.return_value": False,
            "append.return_value": True,
            "prepend.return_value": True,
        },
    )
    mocker.patch.object(ensure_path_module, "userpath", mocked)
    return mocked


def test_ensure_path_dry_run_does_not_append(mock_userpath: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    path_added, _ = ensure_path_module.ensure_path(
        Path("/some/bin"), force=True, prepend=False, all_shells=False, dry_run=True
    )

    assert (path_added, mock_userpath.append.called, mock_userpath.prepend.called, capsys.readouterr().out) == (
        False,
        False,
        False,
        "Would append /some/bin to the PATH environment variable.\n",
    )


def test_ensure_path_dry_run_reports_prepend(mock_userpath: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    ensure_path_module.ensure_path(Path("/some/bin"), force=True, prepend=True, all_shells=False, dry_run=True)

    assert (mock_userpath.prepend.called, "Would prepend" in capsys.readouterr().out) == (False, True)


def test_ensure_path_non_dry_run_still_appends(
    mock_userpath: MagicMock, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    location: Final[Path] = Path("/some/bin")

    ensure_path_module.ensure_path(location, force=True, prepend=False, all_shells=False, dry_run=False)

    assert (mock_userpath.append.call_args_list, "Success!" in capsys.readouterr().out) == (
        [mocker.call(str(location), "pipx", all_shells=False)],
        True,
    )


def test_ensure_pipx_paths_dry_run_footer(mock_userpath: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code: Final = ensure_path_module.ensure_pipx_paths(
        force=True, prepend=False, all_shells=False, dry_run=True, is_global=False
    )

    out: Final[str] = capsys.readouterr().out.lower()
    assert (exit_code, mock_userpath.append.called, "dry run" in out, "no changes were made" in out) == (
        EXIT_CODE_OK,
        False,
        True,
        True,
    )


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
@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_updates_system_profile(
    mocker: MockerFixture, tmp_path: Path, macos: bool, prepend: bool, expected: str
) -> None:
    (config_file := tmp_path / "etc/profile.d/pipx.sh").parent.mkdir(parents=True)
    mocker.patch.object(type(paths.CTX), "bin_dir", mocker.PropertyMock(return_value=Path("/opt/pipx/bin")))
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", macos)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=prepend, all_shells=False, dry_run=False, is_global=True)

    assert config_file.read_text() == expected


@pytest.mark.parametrize(
    ("macos", "existing"),
    [
        pytest.param(False, "# site settings\nexport PIPX_GLOBAL_HOME=/srv/pipx\n", id="linux-foreign"),
        pytest.param(
            False,
            'case ":$PATH:" in *:/site/bin:*) ;; *) export PATH="$PATH":/site/bin:/site/sbin ;; esac\n',
            id="linux-similar-foreign-line",
        ),
        pytest.param(True, "/site/bin\n/other/bin\n", id="macos-foreign"),
    ],
)
@_SKIP_GLOBAL_ON_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_ensurepath_cli_global_keeps_foreign_file(
    mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str], macos: bool, existing: str
) -> None:
    (config_file := tmp_path / "pipx.sh").write_text(existing, encoding="utf-8")
    config_file.chmod(0o640)
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", macos)

    assert (
        run_pipx_cli(["ensurepath", "--global"]),
        config_file.read_text(encoding="utf-8"),
        stat.S_IMODE(config_file.stat().st_mode),
        "pass --force to replace the file" in " ".join(capsys.readouterr().err.split()),
    ) == (1, existing, 0o640, True)


@pytest.fixture(params=[pytest.param(False, id="linux"), pytest.param(True, id="macos")])
def undecodable_config_file(request: pytest.FixtureRequest, mocker: MockerFixture, tmp_path: Path) -> Path:
    (config_file := tmp_path / "pipx.sh").write_bytes(b"/site/\xff\n")
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", request.param)
    return config_file


@_SKIP_GLOBAL_ON_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_ensurepath_cli_global_keeps_undecodable_file(
    undecodable_config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        run_pipx_cli(["ensurepath", "--global"]),
        undecodable_config_file.read_bytes(),
        "pass --force to replace the file" in " ".join(capsys.readouterr().err.split()),
    ) == (1, b"/site/\xff\n", True)


@_SKIP_GLOBAL_ON_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_ensurepath_cli_global_force_replaces_undecodable_file(undecodable_config_file: Path) -> None:
    assert (
        run_pipx_cli(["ensurepath", "--global", "--force"]),
        str(paths.CTX.bin_dir) in undecodable_config_file.read_text(encoding="utf-8"),
    ) == (EXIT_CODE_OK, True)


@_SKIP_GLOBAL_ON_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_ensurepath_cli_global_force_replaces_foreign_file(mocker: MockerFixture, tmp_path: Path) -> None:
    (config_file := tmp_path / "pipx.sh").write_text("/site/bin\n/other/bin\n", encoding="utf-8")
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", True)

    assert (run_pipx_cli(["ensurepath", "--global", "--force"]), config_file.read_text(encoding="utf-8")) == (
        EXIT_CODE_OK,
        f"{paths.CTX.bin_dir}\n",
    )


@pytest.mark.parametrize(
    ("macos", "prepend", "existing", "expected"),
    [
        pytest.param(
            False,
            True,
            """case ":$PATH:" in *:'/old dir/bin':*) ;; *) export PATH="$PATH":'/old dir/bin' ;; esac\n""",
            'case ":$PATH:" in *:/srv/pipx/bin:*) ;; *) export PATH=/srv/pipx/bin:"$PATH" ;; esac\n',
            id="linux",
        ),
        pytest.param(True, False, "/old/bin\n", "/srv/pipx/bin\n", id="macos"),
    ],
)
@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_replaces_own_entry(
    mocker: MockerFixture, tmp_path: Path, *, macos: bool, prepend: bool, existing: str, expected: str
) -> None:
    (config_file := tmp_path / "pipx.sh").write_text(existing, encoding="utf-8")
    mocker.patch.object(type(paths.CTX), "bin_dir", mocker.PropertyMock(return_value=Path("/srv/pipx/bin")))
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", macos)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=prepend, all_shells=False, dry_run=False, is_global=True)

    assert config_file.read_text(encoding="utf-8") == expected


@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_skips_userpath(
    mock_userpath: MagicMock, mocker: MockerFixture, tmp_path: Path
) -> None:
    config_file: Final[Path] = tmp_path / "pipx.sh"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=False, all_shells=False, dry_run=False, is_global=True)

    assert (mock_userpath.append.called, config_file.is_file()) == (False, True)


@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_dry_run_does_not_write(
    mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file: Final[Path] = tmp_path / "pipx.sh"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=False, all_shells=False, dry_run=True, is_global=True)

    # pipx wraps the message, so a long temp path moves the line break into the phrase
    assert (
        config_file.exists(),
        "no changes were made to the system PATH" in " ".join(capsys.readouterr().out.split()),
    ) == (False, True)


@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_configuration_is_world_readable(mocker: MockerFixture, tmp_path: Path) -> None:
    config_file: Final[Path] = tmp_path / "pipx"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    previous_umask: Final[int] = os.umask(0o077)
    try:
        ensure_path_module.ensure_pipx_paths(
            force=False, prepend=False, all_shells=False, dry_run=False, is_global=True
        )
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(config_file.stat().st_mode) == 0o644


@_SKIP_GLOBAL_ON_WINDOWS
def test_ensure_pipx_paths_global_reports_existing_configuration(
    mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (config_file := tmp_path / "pipx.sh").write_text(f"{paths.CTX.bin_dir}\n")
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)
    mocker.patch.object(ensure_path_module, "MACOS", True)

    ensure_path_module.ensure_pipx_paths(force=False, prepend=False, all_shells=False, dry_run=False, is_global=True)

    # pipx wraps the message, so a long temp path moves the line break into the phrase
    assert "already in the system PATH" in " ".join(capsys.readouterr().out.split())


@_SKIP_GLOBAL_ON_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_ensurepath_cli_global_writes_system_configuration(mocker: MockerFixture, tmp_path: Path) -> None:
    config_file: Final[Path] = tmp_path / "pipx"
    mocker.patch.object(ensure_path_module, "_GLOBAL_PATH_FILE", config_file)

    assert (run_pipx_cli(["ensurepath", "--global"]), config_file.exists()) == (EXIT_CODE_OK, True)
