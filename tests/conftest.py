from __future__ import annotations

import hashlib
import importlib
import io
import logging
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from venv import EnvBuilder

import pytest

from helpers import PACKAGE_CACHE_DIR_NAME, WIN, app_name, run_pipx_cli
from pipx import commands, interpreter, paths, shared_libs, standalone_python, venv
from pipx.backends import get_backend
from pipx.backends import pip as _pip_backend_module
from pipx.backends import uv as _uv_backend_module
from pipx.backends.uv import find_uv_binary
from pipx.commands import common
from pipx.venv import reset_backend_override_warnings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

    from pytest_mock import MockerFixture

# ``pipx.commands.__init__`` re-exports ``upgrade`` (the function), which shadows the submodule on the package.
# ``import_module`` returns the module regardless.
_UPGRADE_MODULE: Final[ModuleType] = importlib.import_module("pipx.commands.upgrade")

_PIPX_TESTS_DIR: Final[Path] = Path(".pipx_tests")
_PIPX_TESTS_PACKAGE_LIST_DIR: Final[Path] = Path("testdata/tests_packages")
_IGNORE_PROJECT_OUTPUT: Final[Callable[[str, list[str]], set[str]]] = shutil.ignore_patterns("build", "*.egg-info")


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).parents[1]


@pytest.fixture
def make_pylock(root: Path, tmp_path: Path) -> Callable[[str, str], Path]:
    def create(package: str, version: str) -> Path:
        wheel = next(
            (root / _PIPX_TESTS_DIR / "package_cache" / PACKAGE_CACHE_DIR_NAME).glob(f"{package}-{version}-*.whl")
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
    # the temp env must be active while the resource is built
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]
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
    # cache reset has no public API
    _uv_backend_module._check_uv_version.cache_clear()  # ruff:ignore[private-member-access]
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


@pytest.fixture(scope="session")
def standalone_python_build(tmp_path_factory: pytest.TempPathFactory) -> tuple[bytes, str]:
    """A local stand-in for a python-build-standalone release archive, shaped like the upstream layout.

    On POSIX ``bin/python3`` is a shim that execs the running interpreter, because copying the binary itself would
    break its relative dylib/RPATH lookups on some builds. On Windows it is the venv launcher beside ``pyvenv.cfg``,
    the same relocatable pair every Windows venv ships. Tests exercise the real download, unpack, and install code
    paths against a working interpreter without touching github.com.
    """
    env_dir = tmp_path_factory.mktemp("standalone_python") / "python"
    if WIN:
        EnvBuilder(with_pip=False).create(env_dir)
        for launcher in (env_dir / "Scripts").glob("*.exe"):
            shutil.copy2(launcher, env_dir / launcher.name)
    else:
        bin_dir = env_dir / "bin"
        bin_dir.mkdir(parents=True)
        shim = bin_dir / "python3"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(env_dir, arcname="python")
    return buffer.getvalue(), "{}.{}.{}".format(*sys.version_info[:3])


@pytest.fixture(scope="session")
def standalone_python_index(standalone_python_build: tuple[bytes, str]) -> Callable[[str], dict[str, object]]:
    archive_bytes, _ = standalone_python_build
    digest = "sha256:" + hashlib.sha256(archive_bytes).hexdigest()

    def build(full_version: str) -> dict[str, object]:
        suffixes = [
            suffix
            for machines in standalone_python.MACHINE_SUFFIX.values()
            for entry in machines.values()
            for suffix_list in (entry.values() if isinstance(entry, dict) else [entry])
            for suffix in suffix_list
        ]
        return {
            "fetched": time.time(),
            "releases": [(f"https://example.invalid/cpython-{full_version}-{suffix}", digest) for suffix in suffixes],
        }

    return build


@pytest.fixture
def mocked_github_api(
    monkeypatch: pytest.MonkeyPatch,
    standalone_python_build: tuple[bytes, str],
    standalone_python_index: Callable[[str], dict[str, object]],
) -> None:
    archive_bytes, full_version = standalone_python_build
    index = standalone_python_index(full_version)
    monkeypatch.setattr(
        standalone_python,
        "get_or_update_index",
        lambda *, use_cache=True: index,  # ruff:ignore[unused-lambda-argument]  # the canned index never goes stale
    )
    monkeypatch.setattr(
        standalone_python,
        "urlopen",
        lambda url, timeout=None: io.BytesIO(archive_bytes),  # ruff:ignore[unused-lambda-argument]  # one archive
    )


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
        config.option.markexpr = (f"{markexpr} or " if markexpr else "") + "all_packages"
    else:
        config.option.markexpr = (f"{markexpr} and " if markexpr else "") + "not all_packages"


@pytest.fixture(scope="session", autouse=True)
def pipx_local_pypiserver(
    request: pytest.FixtureRequest, root: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    if request.config.option.net_pypiserver:
        # need both yield and return because other codepath has both
        yield ""
        return

    pipx_cache_dir = root / _PIPX_TESTS_DIR / "package_cache"
    update_cache = [sys.executable, "scripts/update_package_cache.py"]
    cache_paths = [str(_PIPX_TESTS_PACKAGE_LIST_DIR), str(pipx_cache_dir)]
    if subprocess.run([*update_cache, "--check-only", *cache_paths], check=False, cwd=root).returncode:
        subprocess.run([*update_cache, *cache_paths], check=True, cwd=root)

    def find_free_port() -> int:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind(("", 0))
            return sock.getsockname()[1]

    port = find_free_port()
    os.environ["NO_PROXY"] = "127.0.0.1"
    cmd = [
        str(Path(sys.executable).parent / "pypi-server"),
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
        "--log-file",
        str(tmp_path_factory.mktemp("log") / "pypiserver.log"),
        str(pipx_cache_dir / PACKAGE_CACHE_DIR_NAME),
    ]
    pypiserver_process = subprocess.Popen(cmd, cwd=root)
    try:
        url = f"http://127.0.0.1:{port}/simple/"
        while True:
            try:
                with urlopen(url) as response:
                    if response.code == HTTPStatus.OK:
                        break
            except (URLError, HTTPError):
                continue
        yield url
    finally:
        pypiserver_process.terminate()
        # reap the child before the Popen is collected, else its finalizer raises ResourceWarning
        pypiserver_process.wait()


@pytest.fixture(scope="session")
def pipx_session_shared_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("session_shareddir")


@pytest.fixture(scope="session")
def utils_path_dirs(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    """One scratch directory of symlinks keeps whatever else lives beside git and uv off PATH, which the ``⚠️`` and
    ``WARNING`` assertions in ``test_install`` depend on. An unelevated Windows user without Developer Mode cannot
    create symlinks, so uv gets copied instead, while git falls back to its own directory: git.exe finds its helpers
    and DLLs relative to its image path, so it only runs from where it was installed.
    """
    tmp_path = tmp_path_factory.mktemp("session_utilstempdir")
    path_dirs = [tmp_path]

    git = shutil.which("git")
    assert git is not None, "git must be on PATH to run the test suite"
    git_path = Path(git)
    try:
        (tmp_path / git_path.name).symlink_to(git_path)
    except OSError:  # no symlink privilege, e.g. Windows raises WinError 1314
        path_dirs.append(git_path.parent)

    if uv := shutil.which("uv"):  # exposed only when present so the uv-backend smoke test can find it
        exposed = tmp_path / Path(uv).name
        try:
            exposed.symlink_to(uv)
        except OSError:
            # uv is standalone, so a copy runs the same and keeps its directory, often ~/.local/bin, off PATH
            shutil.copy2(uv, exposed)

    return path_dirs


@pytest.fixture
def pipx_temp_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipx_session_shared_dir: Path,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    *,
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    """Shared libs are built once per session; every other pipx dir is recreated per test function."""
    _pipx_temp_env_helper(
        pipx_session_shared_dir, tmp_path, monkeypatch, request, utils_path_dirs, pypi=pipx_local_pypiserver
    )
    yield
    monkeypatch.undo()
    paths.ctx.make_local()


@pytest.fixture
def pipx_ultra_temp_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    """Every test function starts as if pipx had never run, shared libs directory included."""
    _pipx_temp_env_helper(
        tmp_path / "shareddir", tmp_path, monkeypatch, request, utils_path_dirs, pypi=pipx_local_pypiserver
    )
    yield
    monkeypatch.undo()
    paths.ctx.make_local()


def _pipx_temp_env_helper(
    pipx_shared_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    *,
    pypi: str,
) -> None:
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_HOME", tmp_path / "subdir" / "pipxhome")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_BIN_DIR", tmp_path / "otherdir" / "pipxbindir")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_MAN_DIR", tmp_path / "otherdir" / "pipxmandir")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_COMPLETION_DIR", tmp_path / "otherdir" / "pipxcompletiondir")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_SHARED_LIBS", pipx_shared_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_HOME", tmp_path / "global" / "pipxhome")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_BIN_DIR", tmp_path / "global_otherdir" / "pipxbindir")
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_MAN_DIR", tmp_path / "global_otherdir" / "pipxmandir")
    monkeypatch.setattr(
        paths, "OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR", tmp_path / "global_otherdir" / "pipxcompletiondir"
    )
    # Refresh paths.ctx to commit the overrides
    paths.ctx.make_local()

    # Each consumer holds its own ``shared_libs`` reference (via
    # ``from pipx.shared_libs import shared_libs``); patch every importer.
    # a fresh instance per test, for which there is no public factory
    monkeypatch.setattr(shared_libs, "shared_libs", shared_libs._SharedLibs())  # ruff:ignore[private-member-access]
    monkeypatch.setattr(venv, "shared_libs", shared_libs.shared_libs)
    monkeypatch.setattr(_pip_backend_module, "shared_libs", shared_libs.shared_libs)
    monkeypatch.setattr(_UPGRADE_MODULE, "shared_libs", shared_libs.shared_libs)

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
    monkeypatch.setenv("PATH", os.pathsep.join(str(entry) for entry in (paths.ctx.bin_dir, *utils_path_dirs)))
    # On Windows, monkeypatch pipx.commands.common._can_symlink_cache to
    #   indicate that paths.ctx.bin_dir and paths.ctx.man_dir
    #   cannot use symlinks, even if we're running as administrator and
    #   symlinks are actually possible.
    if WIN:
        # seeding the symlink cache has no public API
        symlink_cache = commands.common._can_symlink_cache  # ruff:ignore[private-member-access]
        monkeypatch.setitem(symlink_cache, paths.ctx.bin_dir, False)
        monkeypatch.setitem(symlink_cache, paths.ctx.man_dir, False)
    if not request.config.option.net_pypiserver:
        # IMPORTANT: use 127.0.0.1 not localhost
        #   Using localhost on Windows creates enormous slowdowns
        #   (for some reason--perhaps IPV6/IPV4 tries, timeouts?)
        monkeypatch.setenv("PIP_INDEX_URL", pypi)
        # uv ignores PIP_INDEX_URL; without UV_INDEX_URL the uv-backend tests
        # would hit real PyPI on CI.
        monkeypatch.setenv("UV_INDEX_URL", pypi)
