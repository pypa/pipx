import os
import subprocess
from pathlib import Path

import pytest  # type: ignore

from helpers import WIN
from pipx import commands, constants, shared_libs, venv


def pytest_addoption(parser):
    parser.addoption(
        "--all-packages",
        action="store_true",
        dest="all_packages",
        default=False,
        help="Run only the long, slow tests installing the maximum list of packages.",
    )
    parser.addoption(
        "--pypiserver",
        action="store_true",
        dest="pypiserver",
        default=False,
        help="Start local pypi server.",
    )


def pytest_configure(config):
    markexpr = getattr(config.option, "markexpr", "")

    if config.option.all_packages:
        new_markexpr = (f"{markexpr} or " if markexpr else "") + "all_packages"
    else:
        new_markexpr = (f"{markexpr} and " if markexpr else "") + "not all_packages"

    config.option.markexpr = new_markexpr


def pipx_temp_env_helper(pipx_shared_dir, tmp_path, monkeypatch):
    home_dir = Path(tmp_path) / "subdir" / "pipxhome"
    bin_dir = Path(tmp_path) / "otherdir" / "pipxbindir"

    monkeypatch.setattr(constants, "PIPX_SHARED_LIBS", pipx_shared_dir)
    monkeypatch.setattr(shared_libs, "shared_libs", shared_libs._SharedLibs())
    monkeypatch.setattr(venv, "shared_libs", shared_libs.shared_libs)

    monkeypatch.setattr(constants, "PIPX_HOME", home_dir)
    monkeypatch.setattr(constants, "LOCAL_BIN_DIR", bin_dir)
    monkeypatch.setattr(constants, "PIPX_LOCAL_VENVS", home_dir / "venvs")
    monkeypatch.setattr(constants, "PIPX_VENV_CACHEDIR", home_dir / ".cache")
    monkeypatch.setattr(constants, "PIPX_LOG_DIR", home_dir / "logs")

    # macOS needs /usr/bin in PATH to compile certain packages, but
    #   applications in /usr/bin cause test_install.py tests to raise warnings
    #   which make tests fail (e.g. on Github ansible apps exist in /usr/bin)
    monkeypatch.setenv("PATH_ORIG", str(bin_dir) + os.pathsep + os.getenv("PATH"))
    monkeypatch.setenv("PATH_TEST", str(bin_dir))
    monkeypatch.setenv("PATH", str(bin_dir))
    # On Windows, monkeypatch pipx.commands.common._can_symlink_cache to
    #   indicate that constants.LOCAL_BIN_DIR cannot use symlinks, even if
    #   we're running as administrator and symlinks are actually possible.
    if WIN:
        monkeypatch.setitem(
            commands.common._can_symlink_cache, constants.LOCAL_BIN_DIR, False
        )


@pytest.fixture(scope="session", autouse=True)
def pipx_local_pypiserver(request):
    """Starts local pypiserver once per session if --pypiserver was passed
    to pytest"""
    packages_dir = request.config.invocation_params.dir / ".pipx_tests_cache"
    if request.config.option.pypiserver:
        print("Starting pypiserver...")
        pypiserver_log_fh = open(
            request.config.invocation_params.dir / "pypiserver.out", "w"
        )
        pypiserver_err_fh = open(
            request.config.invocation_params.dir / "pypiserver.err", "w"
        )
        pypiserver_process = subprocess.Popen(
            [
                "pypi-server",
                "--authenticate=update",
                "--disable-fallback",
                str(packages_dir),
            ],
            universal_newlines=True,
            stdout=pypiserver_log_fh,
            stderr=pypiserver_err_fh,
        )
        print("pypiserver Started.")
    yield
    if request.config.option.pypiserver:
        pypiserver_process.terminate()
        pypiserver_log_fh.close()
        pypiserver_err_fh.close()


@pytest.fixture(scope="session")
def pipx_session_shared_dir(tmp_path_factory):
    """Makes a temporary pipx shared libs directory only once per session"""
    return tmp_path_factory.mktemp("session_shareddir")


@pytest.fixture
def pipx_temp_env(tmp_path, monkeypatch, pipx_session_shared_dir):
    """Sets up temporary paths for pipx to install into.

    Shared libs are setup once per session, all other pipx dirs, constants are
    recreated for every test function.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    pipx_temp_env_helper(pipx_session_shared_dir, tmp_path, monkeypatch)


@pytest.fixture
def pipx_ultra_temp_env(tmp_path, monkeypatch):
    """Sets up temporary paths for pipx to install into.

    Fully temporary environment, every test function starts as if pipx has
    never been run before, including empty shared libs directory.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    shared_dir = Path(tmp_path) / "shareddir"
    pipx_temp_env_helper(shared_dir, tmp_path, monkeypatch)
