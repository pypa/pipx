import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest  # type: ignore

from helpers import WIN
from pipx import commands, constants, interpreter, shared_libs, venv

PIPX_TESTS_DIR = Path(".pipx_tests")
PIPX_TESTS_PACKAGE_LIST_DIR = Path("testdata/tests_packages")


def pytest_addoption(parser):
    parser.addoption(
        "--all-packages",
        action="store_true",
        dest="all_packages",
        default=False,
        help="Run only the long, slow tests installing the maximum list of packages.",
    )
    parser.addoption(
        "--net-pypiserver",
        action="store_true",
        dest="net_pypiserver",
        default=False,
        help="Start local pypi server and use in tests.",
    )


def pytest_configure(config):
    markexpr = getattr(config.option, "markexpr", "")

    if config.option.all_packages:
        new_markexpr = (f"{markexpr} or " if markexpr else "") + "all_packages"
    else:
        new_markexpr = (f"{markexpr} and " if markexpr else "") + "not all_packages"

    config.option.markexpr = new_markexpr


def pipx_temp_env_helper(
    pipx_shared_dir, tmp_path, monkeypatch, request, utils_temp_dir
):
    home_dir = Path(tmp_path) / "subdir" / "pipxhome"
    bin_dir = Path(tmp_path) / "otherdir" / "pipxbindir"
    global_bin_dir = Path(tmp_path) / "global" / "pipxbindir"
    global_home_dir = Path(tmp_path) / "global" / "pipxhome"

    # Patch in test specific base paths
    monkeypatch.setattr(constants.PIPX_DIRS, "_base_shared_libs", pipx_shared_dir)
    monkeypatch.setattr(constants.PIPX_DIRS, "_base_home", home_dir)
    monkeypatch.setattr(constants.PIPX_DIRS, "_base_bin", bin_dir)
    # Patch the default global paths so developers don't contaminate their own systems
    monkeypatch.setattr(constants, "DEFAULT_PIPX_GLOBAL_BIN_DIR", global_bin_dir)
    monkeypatch.setattr(constants, "DEFAULT_PIPX_GLOBAL_HOME", global_home_dir)
    monkeypatch.setattr(shared_libs, "shared_libs", shared_libs._SharedLibs())
    monkeypatch.setattr(venv, "shared_libs", shared_libs.shared_libs)
    monkeypatch.setattr(interpreter, "DEFAULT_PYTHON", sys.executable)

    if "PIPX_DEFAULT_PYTHON" in os.environ:
        monkeypatch.delenv("PIPX_DEFAULT_PYTHON")

    # macOS needs /usr/bin in PATH to compile certain packages, but
    #   applications in /usr/bin cause test_install.py tests to raise warnings
    #   which make tests fail (e.g. on Github ansible apps exist in /usr/bin)
    monkeypatch.setenv(
        "PATH_ORIG", str(constants.PIPX_DIRS.BIN_DIR) + os.pathsep + os.getenv("PATH")
    )
    monkeypatch.setenv("PATH_TEST", str(constants.PIPX_DIRS.BIN_DIR))
    monkeypatch.setenv(
        "PATH", str(constants.PIPX_DIRS.BIN_DIR) + os.pathsep + str(utils_temp_dir)
    )
    # On Windows, monkeypatch pipx.commands.common._can_symlink_cache to
    #   indicate that constants.PIPX_DIRS.BIN_DIR cannot use symlinks, even if
    #   we're running as administrator and symlinks are actually possible.
    if WIN:
        monkeypatch.setitem(
            commands.common._can_symlink_cache, constants.PIPX_DIRS.BIN_DIR, False
        )
    if not request.config.option.net_pypiserver:
        # IMPORTANT: use 127.0.0.1 not localhost
        #   Using localhost on Windows creates enormous slowdowns
        #   (for some reason--perhaps IPV6/IPV4 tries, timeouts?)
        monkeypatch.setenv(
            "PIP_INDEX_URL", "http://username:password@127.0.0.1:8080/simple"
        )


@pytest.fixture(scope="session", autouse=True)
def pipx_local_pypiserver(request):
    """Starts local pypiserver once per session unless --net-pypiserver was
    passed to pytest"""
    if request.config.option.net_pypiserver:
        # need both yield and return because other codepath has both
        yield
        return

    pipx_cache_dir = (
        request.config.invocation_params.dir / PIPX_TESTS_DIR / "package_cache"
    )
    check_test_packages_cmd = [
        sys.executable,
        "scripts/update_package_cache.py",
        "--check-only",
        str(PIPX_TESTS_PACKAGE_LIST_DIR),
        str(pipx_cache_dir),
    ]
    update_test_packages_cmd = [
        sys.executable,
        "scripts/update_package_cache.py",
        str(PIPX_TESTS_PACKAGE_LIST_DIR),
        str(pipx_cache_dir),
    ]
    check_test_packages_process = subprocess.run(check_test_packages_cmd)
    if check_test_packages_process.returncode != 0:
        raise Exception(
            f"Directory {str(pipx_cache_dir)} does not contain all "
            "package distribution files necessary to run pipx tests. Please "
            "run the following command to populate it: "
            f"{' '.join(update_test_packages_cmd)}"
        )

    with open(
        request.config.invocation_params.dir / PIPX_TESTS_DIR / "pypiserver.log", "w"
    ) as pypiserver_err_fh:
        pypiserver_htpasswd = str(
            request.config.invocation_params.dir / PIPX_TESTS_DIR / "htpasswd"
        )

        from passlib.apache import HtpasswdFile  # type: ignore

        ht = HtpasswdFile(pypiserver_htpasswd, new=True)
        ht.set_password("username", "password")
        ht.save()

        pypiserver_process = subprocess.Popen(
            [
                "pypi-server",
                "run",
                "--verbose",
                "--authenticate=update,download,list",
                f"--passwords={pypiserver_htpasswd}",
                "--disable-fallback",
                str(pipx_cache_dir / f"{sys.version_info[0]}.{sys.version_info[1]}"),
            ],
            universal_newlines=True,
            stderr=pypiserver_err_fh,
        )

        yield

        pypiserver_process.terminate()


@pytest.fixture(scope="session")
def pipx_session_shared_dir(tmp_path_factory):
    """Makes a temporary pipx shared libs directory only once per session"""
    return tmp_path_factory.mktemp("session_shareddir")


@pytest.fixture(scope="session")
def utils_temp_dir(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("session_utilstempdir")
    utils = ["git"]
    for util in utils:
        util_path = Path(shutil.which(util))
        try:
            (tmp_path / util_path.name).symlink_to(util_path)
        except FileExistsError:
            pass
    return tmp_path


@pytest.fixture
def pipx_temp_env(
    tmp_path, monkeypatch, pipx_session_shared_dir, request, utils_temp_dir
):
    """Sets up temporary paths for pipx to install into.

    Shared libs are setup once per session, all other pipx dirs, constants are
    recreated for every test function.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    pipx_temp_env_helper(
        pipx_session_shared_dir, tmp_path, monkeypatch, request, utils_temp_dir
    )


@pytest.fixture
def pipx_ultra_temp_env(tmp_path, monkeypatch, request, utils_temp_dir):
    """Sets up temporary paths for pipx to install into.

    Fully temporary environment, every test function starts as if pipx has
    never been run before, including empty shared libs directory.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    shared_dir = Path(tmp_path) / "shareddir"
    pipx_temp_env_helper(shared_dir, tmp_path, monkeypatch, request, utils_temp_dir)
