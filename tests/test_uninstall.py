import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli
from package_info import PKG
from pipx import constants, util


def test_uninstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_multiple_same_app(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "kaggle==1.5.9", "--include-deps"])
    assert not run_pipx_cli(["uninstall", "kaggle"])


def test_uninstall_circular_deps(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", PKG["cloudtoken"]["spec"]])
    assert not run_pipx_cli(["uninstall", "cloudtoken"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_uninstall_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_suffix(pipx_temp_env, capsys):
    name = "pbr"
    suffix = "_a"
    executable = f"{name}{suffix}{'.exe' if constants.WINDOWS else ''}"

    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    assert (constants.LOCAL_BIN_DIR / executable).exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not (constants.LOCAL_BIN_DIR / executable).exists()


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_uninstall_suffix_legacy_venv(pipx_temp_env, capsys, metadata_version):
    name = "pbr"
    suffix = "_a"
    executable = f"{name}{suffix}{'.exe' if constants.WINDOWS else ''}"

    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert (constants.LOCAL_BIN_DIR / executable).exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not (constants.LOCAL_BIN_DIR / executable).exists()


def test_uninstall_with_missing_interpreter(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert python_path.is_file()
    python_path.unlink()
    assert not python_path.is_file()

    assert not run_pipx_cli(["uninstall", "pycowsay"])
