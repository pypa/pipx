from unittest import mock

from helpers import run_pipx_cli
from pipx import constants


@mock.patch('pipx.commands.common.expose_apps_globally')
def test_select(mock_expose_apps_globally: mock.Mock, pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["install", "shell-functools==0.3.0", "--suffix", "_3"])
    assert not run_pipx_cli(["select", "shell-functools_3"])

    args, _kwargs = mock_expose_apps_globally.call_args
    app_paths = args[1]

    assert len(app_paths) > 0
    for app_path in app_paths:
        assert app_path.parent.parent.name == "shell-functools_3"


def test_select_no_shadow(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["install", "shell-functools"])
    # don't allow select when it would shadow the package with no prefix
    assert run_pipx_cli(["select", "shell-functools_2"])


def test_select_no_overwrite_with_install(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    # don't allow install when it would overwrite existing binaries/symlinks pointing to a selected venv
    assert run_pipx_cli(["install", "shell-functools"])


def test_select_uninstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert not run_pipx_cli(["uninstall", "shell-functools_2"])

    # check if links are gone
    for app in ["filter", "foldl", "ft-functions", "map"]:
        app_path = constants.LOCAL_BIN_DIR / app
        print(f"app path: {app_path}")
        assert not app_path.exists()


# TODO: test upgrade
# TODO: test reselect
# TODO: add deselect command
# TODO: fix uninstall for Windows

