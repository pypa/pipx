from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import sysconfig
from contextlib import closing, suppress
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from helpers import WIN, app_name, run_pipx_cli
from pipx import commands, interpreter, paths, shared_libs, standalone_python, venv
from pipx.backends import get_backend
from pipx.backends import pip as _pip_backend_module
from pipx.backends import uv as _uv_backend_module
from pipx.backends.uv import find_uv_binary
from pipx.commands import common
from pipx.venv import reset_backend_override_warnings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pytest_mock import MockerFixture

# ``pipx.commands.__init__`` re-exports ``upgrade`` (the function), which
# shadows the submodule on the package. ``import_module`` returns the module
# regardless.
_upgrade_module = importlib.import_module("pipx.commands.upgrade")

PIPX_TESTS_DIR = Path(".pipx_tests")
PIPX_TESTS_PACKAGE_LIST_DIR = Path("testdata/tests_packages")
# Mirrors scripts/test_packages_support.py: free-threaded builds seed a cache of cp3XXt wheels separate from the
# same-version GIL build's directory.
_PACKAGE_CACHE_DIR_NAME: Final[str] = (
    f"{sys.version_info[0]}.{sys.version_info[1]}{'t' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''}"
)
_IGNORE_PROJECT_OUTPUT: Final[Callable[[str, list[str]], set[str]]] = shutil.ignore_patterns("build", "*.egg-info")


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).parents[1]


@pytest.fixture
def make_pylock(root: Path, tmp_path: Path) -> Callable[[str, str], Path]:
    def create(package: str, version: str) -> Path:
        wheel = next(
            (root / PIPX_TESTS_DIR / "package_cache" / _PACKAGE_CACHE_DIR_NAME).glob(f"{package}-{version}-*.whl")
        )
        lock_file = tmp_path / "pylock.test.toml"
        lock_file.write_text(
            f"""lock-version = "1.0"
created-by = "pipx tests"

[[packages]]
name = "{package}"
version = "{version}"

[[packages.wheels]]
name = "{wheel.name}"
url = "{wheel.as_uri()}"

[packages.wheels.hashes]
sha256 = "{hashlib.sha256(wheel.read_bytes()).hexdigest()}"
""",
            encoding="utf-8",
        )
        return lock_file

    return create


@pytest.fixture
def make_project_with_dependency(root: Path, tmp_path: Path) -> Callable[[str], Path]:
    def create(dependency: str) -> Path:
        project = tmp_path / "locked-project"
        shutil.copytree(root / "testdata/empty_project", project, ignore=_IGNORE_PROJECT_OUTPUT)
        pyproject = project / "pyproject.toml"
        pyproject.write_text(
            pyproject.read_text(encoding="utf-8").replace(
                'requires-python = ">=3.10"\n',
                f'dependencies = ["{dependency}"]\nrequires-python = ">=3.10"\n',
            ),
            encoding="utf-8",
        )
        return project

    return create


@pytest.fixture
def inline_script(tmp_path: Path) -> Path:
    script: Final[Path] = tmp_path / "hello.py"
    script.write_text(
        """# /// script
# dependencies = ["pycowsay"]
# requires-python = ">=3.10"
# ///
import pycowsay

print("installed")
""",
        encoding="utf-8",
    )
    return script


@pytest.fixture
def local_extras_project(root: Path, tmp_path: Path) -> Path:
    project: Final[Path] = tmp_path / "local_extras"
    shutil.copytree(root / "testdata/test_package_specifier/local_extras", project, ignore=_IGNORE_PROJECT_OUTPUT)
    return project


@pytest.fixture
def copied_dependency_resource(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the resource is built
    make_project_with_dependency: Callable[[str], Path],
    mocker: MockerFixture,
) -> tuple[Path, bytes]:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    first_project: Final[Path] = make_project_with_dependency("pycowsay==0.0.0.2")
    exposed_app: Final[Path] = paths.ctx.bin_dir / app_name("pycowsay")
    assert not run_pipx_cli(["install", str(first_project), "--include-deps"])
    return exposed_app, exposed_app.read_bytes()


@pytest.fixture
def empty_project(root: Path, tmp_path: Path) -> Path:
    project: Final[Path] = tmp_path / "empty_project"
    shutil.copytree(root / "testdata/empty_project", project, ignore=_IGNORE_PROJECT_OUTPUT)
    return project


@pytest.fixture(autouse=True)
def _backend_test_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin every test to pip with empty backend caches.

    Without the env pin, unit tests that build a ``Venv`` outside the
    ``pipx_temp_env`` fixture would auto-detect uv from CI's PATH and fork a
    real ``uv --version`` probe. Cache resets stop the previous test's
    monkeypatched ``shutil.which`` from poisoning this one.

    Uv-backend tests opt back in with ``--backend uv``.
    """
    monkeypatch.setenv("PIPX_DEFAULT_BACKEND", "pip")
    find_uv_binary.cache_clear()
    _uv_backend_module._check_uv_version.cache_clear()  # ruff:ignore[private-member-access]  # cache reset has no public API
    get_backend.cache_clear()
    reset_backend_override_warnings()


@pytest.fixture(autouse=True)
def _isolate_pipx_logging() -> Iterator[None]:
    yield
    # setup_logging binds a StreamHandler to whatever sys.stderr is when it runs. pytest swaps that stream per
    # test, so a handler left by an earlier verbose run keeps a stale reference and, on a Windows cp1252 console,
    # crashes ("--- Logging error ---") the moment a later test logs a non-ASCII record. Drop pipx's handlers
    # after each test to keep that state from leaking across tests.
    pipx_logger: Final[logging.Logger] = logging.getLogger("pipx")
    for handler in pipx_logger.handlers[:]:
        pipx_logger.removeHandler(handler)
        handler.close()


@pytest.fixture
def mocked_github_api(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """
    Fixture to replace the github index with a local copy,
    to prevent unit tests from exceeding github's API request limit.
    """
    with Path(root / "testdata" / "standalone_python_index_20250818.json").open(encoding="utf-8") as f:
        index = json.load(f)
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda *, use_cache=True: index)  # ruff:ignore[unused-lambda-argument]  # mock ignores use_cache


def pytest_addoption(parser: pytest.Parser) -> None:
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


def pytest_configure(config: pytest.Config) -> None:
    markexpr = getattr(config.option, "markexpr", "")

    if config.option.all_packages:
        new_markexpr = (f"{markexpr} or " if markexpr else "") + "all_packages"
    else:
        new_markexpr = (f"{markexpr} and " if markexpr else "") + "not all_packages"

    config.option.markexpr = new_markexpr


def pipx_temp_env_helper(
    pipx_shared_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_temp_dir: Path,
    *,
    pypi: str,
) -> None:
    home_dir = Path(tmp_path) / "subdir" / "pipxhome"
    bin_dir = Path(tmp_path) / "otherdir" / "pipxbindir"
    man_dir = Path(tmp_path) / "otherdir" / "pipxmandir"
    completion_dir = Path(tmp_path) / "otherdir" / "pipxcompletiondir"

    global_home_dir = Path(tmp_path) / "global" / "pipxhome"
    global_bin_dir = Path(tmp_path) / "global_otherdir" / "pipxbindir"
    global_completion_dir = Path(tmp_path) / "global_otherdir" / "pipxcompletiondir"
    global_man_dir = Path(tmp_path) / "global_otherdir" / "pipxmandir"

    # Patch in test specific paths
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_HOME", home_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_BIN_DIR", bin_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_MAN_DIR", man_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_COMPLETION_DIR", completion_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_SHARED_LIBS", pipx_shared_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_HOME", global_home_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_BIN_DIR", global_bin_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_MAN_DIR", global_man_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR", global_completion_dir)
    # Refresh paths.ctx to commit the overrides
    paths.ctx.make_local()

    # Each consumer holds its own ``shared_libs`` reference (via
    # ``from pipx.shared_libs import shared_libs``); patch every importer.
    monkeypatch.setattr(shared_libs, "shared_libs", shared_libs._SharedLibs())  # ruff:ignore[private-member-access]  # fresh instance per test, no public factory
    monkeypatch.setattr(venv, "shared_libs", shared_libs.shared_libs)
    monkeypatch.setattr(_pip_backend_module, "shared_libs", shared_libs.shared_libs)
    monkeypatch.setattr(_upgrade_module, "shared_libs", shared_libs.shared_libs)

    if "PIPX_DEFAULT_PYTHON" in os.environ:
        monkeypatch.delenv("PIPX_DEFAULT_PYTHON")
    interpreter.get_default_python.cache_clear()
    # CI runners ship uv on PATH; pin every legacy test to pip so the auto-
    # detect doesn't silently flip them. Uv-backend tests opt in with --backend uv.
    monkeypatch.setenv("PIPX_DEFAULT_BACKEND", "pip")

    # macOS needs /usr/bin in PATH to compile certain packages, but
    #   applications in /usr/bin cause test_install.py tests to raise warnings
    #   which make tests fail (e.g. on Github ansible apps exist in /usr/bin)
    monkeypatch.setenv("PATH_ORIG", str(paths.ctx.bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("PATH_TEST", str(paths.ctx.bin_dir))
    monkeypatch.setenv("PATH", str(paths.ctx.bin_dir) + os.pathsep + str(utils_temp_dir))
    # On Windows, monkeypatch pipx.commands.common._can_symlink_cache to
    #   indicate that paths.ctx.bin_dir and paths.ctx.man_dir
    #   cannot use symlinks, even if we're running as administrator and
    #   symlinks are actually possible.
    if WIN:
        monkeypatch.setitem(commands.common._can_symlink_cache, paths.ctx.bin_dir, False)  # ruff:ignore[private-member-access]  # seeding the symlink cache has no public API
        monkeypatch.setitem(commands.common._can_symlink_cache, paths.ctx.man_dir, False)  # ruff:ignore[private-member-access]  # seeding the symlink cache has no public API
    if not request.config.option.net_pypiserver:
        # IMPORTANT: use 127.0.0.1 not localhost
        #   Using localhost on Windows creates enormous slowdowns
        #   (for some reason--perhaps IPV6/IPV4 tries, timeouts?)
        monkeypatch.setenv("PIP_INDEX_URL", pypi)
        # uv ignores PIP_INDEX_URL; without UV_INDEX_URL the uv-backend tests
        # would hit real PyPI on CI.
        monkeypatch.setenv("UV_INDEX_URL", pypi)


@pytest.fixture(scope="session", autouse=True)
def pipx_local_pypiserver(
    request: pytest.FixtureRequest, root: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    """Starts local pypiserver once per session unless --net-pypiserver was
    passed to pytest"""
    if request.config.option.net_pypiserver:
        # need both yield and return because other codepath has both
        yield ""
        return

    pipx_cache_dir = root / PIPX_TESTS_DIR / "package_cache"
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
    check_test_packages_process = subprocess.run(check_test_packages_cmd, check=False, cwd=root)
    if check_test_packages_process.returncode != 0:
        subprocess.run(update_test_packages_cmd, check=True, cwd=root)

    def find_free_port() -> int:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    server_log = tmp_path_factory.mktemp("log") / "pypiserver.log"
    if server_log.exists():
        server_log.unlink()
    port = find_free_port()
    os.environ["NO_PROXY"] = "127.0.0.1"
    cache = str(pipx_cache_dir / _PACKAGE_CACHE_DIR_NAME)
    server = str(Path(sys.executable).parent / "pypi-server")
    cmd = [
        server,
        "run",
        "--verbose",
        "--disable-fallback",
        "--backend",
        "cached-dir",
        "--cache-control=3600",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        cache,
    ]
    cmd += ["--log-file", str(server_log)]
    pypiserver_process = subprocess.Popen(cmd, cwd=root)
    url = f"http://127.0.0.1:{port}/simple/"
    while True:
        try:
            with urlopen(url) as response:
                if response.code == HTTPStatus.OK:
                    break
        except (URLError, HTTPError):
            continue
    yield url
    pypiserver_process.terminate()


@pytest.fixture(scope="session")
def pipx_session_shared_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Makes a temporary pipx shared libs directory only once per session"""
    return tmp_path_factory.mktemp("session_shareddir")


@pytest.fixture(scope="session")
def utils_temp_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp("session_utilstempdir")
    required = ["git"]
    optional = ["uv"]  # exposed only when present so the uv-backend smoke test can find it
    for util in required:
        at_path = shutil.which(util)
        assert at_path is not None
        util_path = Path(at_path)
        with suppress(FileExistsError):
            (tmp_path / util_path.name).symlink_to(util_path)
    for util in optional:
        at_path = shutil.which(util)
        if at_path is None:
            continue
        util_path = Path(at_path)
        with suppress(FileExistsError):
            (tmp_path / util_path.name).symlink_to(util_path)
    return tmp_path


@pytest.fixture
def pipx_temp_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipx_session_shared_dir: Path,
    request: pytest.FixtureRequest,
    utils_temp_dir: Path,
    *,
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    """Sets up temporary paths for pipx to install into.

    Shared libs are setup once per session, all other pipx dirs, constants are
    recreated for every test function.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    pipx_temp_env_helper(
        pipx_session_shared_dir, tmp_path, monkeypatch, request, utils_temp_dir, pypi=pipx_local_pypiserver
    )
    yield
    monkeypatch.undo()
    paths.ctx.make_local()


@pytest.fixture
def pipx_ultra_temp_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_temp_dir: Path,
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    """Sets up temporary paths for pipx to install into.

    Fully temporary environment, every test function starts as if pipx has
    never been run before, including empty shared libs directory.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    shared_dir = Path(tmp_path) / "shareddir"
    pipx_temp_env_helper(shared_dir, tmp_path, monkeypatch, request, utils_temp_dir, pypi=pipx_local_pypiserver)
    yield
    monkeypatch.undo()
    paths.ctx.make_local()
