import sys

import pytest  # type: ignore

from helpers import app_name, mock_legacy_venv, remove_venv_interpreter, run_pipx_cli
from package_info import PKG
from pipx import paths


def file_or_symlink(filepath):
    # Returns True for file or broken symlink or non-broken symlink
    # Returns False for no file and no symlink

    # filepath.exists() returns True for regular file or non-broken symlink
    # filepath.exists() returns False for no regular file or broken symlink
    # filepath.is_symlink() returns True for broken or non-broken symlink
    return filepath.exists() or filepath.is_symlink()


def test_uninstall(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_global(pipx_temp_env):
    if sys.platform.startswith("win"):
        pytest.skip("This behavior is undefined on Windows")
    assert not run_pipx_cli(["--global", "install", "pycowsay"])
    assert not run_pipx_cli(["--global", "uninstall", "pycowsay"])


def test_uninstall_circular_deps(pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["cloudtoken"]["spec"]])
    assert not run_pipx_cli(["uninstall", "cloudtoken"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_uninstall_legacy_venv(pipx_temp_env, metadata_version):
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not file_or_symlink(executable_path)


def test_uninstall_suffix(pipx_temp_env):
    name = "pbr"
    suffix = "_a"
    executable_path = paths.ctx.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


def test_uninstall_injected(pipx_temp_env):
    pycowsay_app_paths = [paths.ctx.bin_dir / app for app in PKG["pycowsay"]["apps"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]
    app_paths = pycowsay_app_paths + pylint_app_paths

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(
        ["inject", "--include-apps", "pycowsay", PKG["pylint"]["spec"]]
    )

    for app_path in app_paths:
        assert app_path.exists()

    assert not run_pipx_cli(["uninstall", "pycowsay"])

    for app_path in app_paths:
        assert not file_or_symlink(app_path)


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_uninstall_suffix_legacy_venv(pipx_temp_env, metadata_version):
    name = "pbr"
    # legacy uninstall on Windows only works with "canonical name characters"
    #   in suffix
    suffix = "-a"
    executable_path = paths.ctx.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


@pytest.mark.parametrize("metadata_version", [None, "0.1", "0.2"])
def test_uninstall_with_missing_interpreter(pipx_temp_env, metadata_version):
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    remove_venv_interpreter("pycowsay")

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    # On Windows we cannot remove app binaries if no metadata and no python
    if not (sys.platform.startswith("win") and metadata_version is None):
        assert not file_or_symlink(executable_path)


@pytest.mark.parametrize("metadata_version", [None, "0.1", "0.2"])
def test_uninstall_proper_dep_behavior(pipx_temp_env, metadata_version):
    # isort is a dependency of pylint.  Make sure that uninstalling pylint
    #   does not also uninstall isort app in LOCAL_BIN_DIR
    isort_app_paths = [paths.ctx.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]

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
        assert not file_or_symlink(pylint_app_path)
    # THIS is what we're making sure is true:
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()


@pytest.mark.parametrize("metadata_version", [None, "0.1", "0.2"])
def test_uninstall_proper_dep_behavior_missing_interpreter(
    pipx_temp_env, metadata_version
):
    # isort is a dependency of pylint.  Make sure that uninstalling pylint
    #   does not also uninstall isort app in LOCAL_BIN_DIR
    isort_app_paths = [paths.ctx.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    remove_venv_interpreter("pylint")
    remove_venv_interpreter("isort")
    for pylint_app_path in pylint_app_paths:
        assert pylint_app_path.exists()
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()

    assert not run_pipx_cli(["uninstall", "pylint"])

    # Do not check the following on Windows without metadata, we do not
    #   remove bin dir links by design for missing interpreter in that case
    if not (sys.platform.startswith("win") and metadata_version is None):
        for pylint_app_path in pylint_app_paths:
            assert not file_or_symlink(pylint_app_path)
    # THIS is what we're making sure is true:
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()
