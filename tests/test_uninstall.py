import sys

import pytest  # type: ignore

from helpers import app_name, mock_legacy_venv, run_pipx_cli
from package_info import PKG
from pipx import constants, util


def test_uninstall(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_multiple_same_app(pipx_temp_env):
    assert not run_pipx_cli(["install", "kaggle==1.5.9", "--include-deps"])
    assert not run_pipx_cli(["uninstall", "kaggle"])


def test_uninstall_circular_deps(pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["cloudtoken"]["spec"]])
    assert not run_pipx_cli(["uninstall", "cloudtoken"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_uninstall_legacy_venv(pipx_temp_env, metadata_version):
    executable_path = constants.LOCAL_BIN_DIR / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    # Also use is_symlink to check for broken symlink.
    #   exists() returns False if symlink exists but target doesn't exist
    assert not executable_path.exists() and not executable_path.is_symlink()


def test_uninstall_suffix(pipx_temp_env):
    name = "pbr"
    suffix = "_a"
    executable_path = constants.LOCAL_BIN_DIR / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    # Also use is_symlink to check for broken symlink.
    #   exists() returns False if symlink exists but target doesn't exist
    assert not executable_path.exists() and not executable_path.is_symlink()


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_uninstall_suffix_legacy_venv(pipx_temp_env, metadata_version):
    name = "pbr"
    # legacy uninstall on Windows only works with "canonical name characters"
    #   in suffix
    suffix = "-a"
    executable_path = constants.LOCAL_BIN_DIR / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    # Also use is_symlink to check for broken symlink.
    #   exists() returns False if symlink exists but target doesn't exist
    assert not executable_path.exists() and not executable_path.is_symlink()


def test_uninstall_with_missing_interpreter(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert python_path.is_file()
    python_path.unlink()
    assert not python_path.is_file()

    assert not run_pipx_cli(["uninstall", "pycowsay"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_uninstall_with_missing_interpreter_legacy_venv(
    pipx_temp_env, metadata_version
):
    executable_path = constants.LOCAL_BIN_DIR / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    _, venv_python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    venv_python_path.unlink()

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    # On Windows we cannot remove app binaries if no metadata and no python
    if not sys.platform.startswith("win"):
        # Also use is_symlink to check for broken symlink.
        #   exists() returns False if symlink exists but target doesn't exist
        assert not executable_path.exists() and not executable_path.is_symlink()


@pytest.mark.parametrize("metadata_version", [None, "0.1", "0.2"])
def test_uninstall_proper_dep_behavior(pipx_temp_env, metadata_version):
    isort_app_paths = [constants.LOCAL_BIN_DIR / app for app in PKG["isort"]["apps"]]
    pylint_app_paths = [constants.LOCAL_BIN_DIR / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    for pylint_app_path in pylint_app_paths:
        assert pylint_app_path.exists()
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()

    assert not run_pipx_cli(["uninstall", "pylint"])

    for pylint_app_path in pylint_app_paths:
        # Also use is_symlink to check for broken symlink.
        #   exists() returns False if symlink exists but target doesn't exist
        assert not pylint_app_path.exists() and not pylint_app_path.is_symlink()
    # THIS is what we're making sure is true:
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()
