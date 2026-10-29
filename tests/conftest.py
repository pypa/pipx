from __future__ import annotations

import hashlib
import importlib
import io
import ipaddress
import logging
import os
import pkgutil
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import types
import zipfile
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final, ParamSpec, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from venv import EnvBuilder

import platformdirs
import pytest
from filelock import FileLock
from flit_core.wheel import make_wheel_in

import pipx
from helpers import PACKAGE_CACHE_DIR_NAME, WIN, MakePylock, app_name, run_pipx_cli, write_import_probe
from pipx import paths, shared_libs, standalone_python, venv
from pipx.backends import get_backend
from pipx.backends import pip as _pip_backend_module
from pipx.backends import uv as _uv_backend_module
from pipx.backends.uv import find_uv_binary, uv_meets_minimum_version
from pipx.commands import common
from pipx.interpreter import get_default_python
from pipx.venv import reset_backend_override_warnings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pytest_mock import MockerFixture

_IGNORE_PROJECT_OUTPUT: Final[Callable[[str, list[str]], set[str]]] = shutil.ignore_patterns("build", "*.egg-info")
_P = ParamSpec("_P")
_R = TypeVar("_R")


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).parents[1]


@pytest.fixture(scope="session")
def package_cache_dir(root: Path) -> Path:
    return root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME


@pytest.fixture
def signal_handlers(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # a signal landing while the main thread runs a weakref callback or finalizer (garbage collection can run at any
    # allocation) raises KeyboardInterrupt there, which the interpreter reports as unraisable; pipx's handler leaves a
    # mark it acts on, so drop that report and keep failing on any other unraisable exception
    report: Final = sys.unraisablehook
    monkeypatch.setattr(
        sys,
        "unraisablehook",
        lambda unraisable: None if issubclass(unraisable.exc_type, KeyboardInterrupt) else report(unraisable),
    )
    # an interrupted pipx ignores further signals, so each test starts from Python's default handlers
    numbers: Final = (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", signal.SIGTERM))
    previous: Final = {number: signal.getsignal(number) for number in numbers}
    signal.signal(signal.SIGINT, signal.default_int_handler)
    yield
    for number, handler in previous.items():
        signal.signal(number, handler)


@pytest.fixture
def before_venv_subprocess(mocker: MockerFixture) -> Callable[[Path, Callable[[], None]], None]:
    def patch(venv_dir: Path, action: Callable[[], None]) -> None:
        # the command list is matched through its repr, which escapes the backslashes of a Windows path
        marker: Final[str] = repr(str(venv_dir))[1:-1]
        mocker.patch.object(subprocess, "Popen", side_effect=_preceded(subprocess.Popen, marker, action))

    return patch


def _preceded(call: Callable[_P, _R], marker: str, action: Callable[[], None]) -> Callable[_P, _R]:
    def preceded(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        if marker in str(args[0]):
            action()
        return call(*args, **kwargs)

    return preceded


@pytest.fixture
def make_pylock(package_cache_dir: Path, tmp_path: Path) -> MakePylock:
    def create(package: str, version: str, group: str | None = None) -> Path:
        wheel: Final[Path] = next(package_cache_dir.glob(f"{package}-{version}-*.whl"))
        groups: Final[str] = "" if group is None else f'dependency-groups = ["{group}"]\ndefault-groups = ["{group}"]\n'
        marker: Final[str] = "" if group is None else f'marker = "\\"{group}\\" in dependency_groups"\n'
        (lock_file := tmp_path / "pylock.test.toml").write_text(
            f"""lock-version = "1.0"
created-by = "pipx tests"
{groups}
[[packages]]
name = "{package}"
version = "{version}"
{marker}
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
        project: Final[Path] = tmp_path / "locked-project"
        shutil.copytree(root / "testdata/empty_project", project, ignore=_IGNORE_PROJECT_OUTPUT)
        pyproject: Final[Path] = project / "pyproject.toml"
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
def make_wheel(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    def create(entries: dict[str, str]) -> Path:
        with zipfile.ZipFile(wheel := tmp_path / "foo_bar_x-1-py3-none-any.whl", "w") as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
        return wheel

    return create


@pytest.fixture
def dotted_app_wheel(make_wheel: Callable[[dict[str, str]], Path]) -> Path:
    # tool.12 carries no shebang, so only its content ties a copy of it to the venv
    return make_wheel({
        "foo_bar_x.py": "def main() -> None:\n    pass\n",
        "foo_bar_x-1.data/scripts/tool.12": "print('tool')\n",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/entry_points.txt": "[console_scripts]\ntool3.12 = foo_bar_x:main\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })


@pytest.fixture
def project_ignoring_project_table(tmp_path: Path) -> Path:
    # stands in for poetry-core<2 or setuptools<61: the backend names the wheel itself and never reads [project]
    project: Final[Path] = tmp_path / "ignores-project-table"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires = []\nbuild-backend = "backend"\nbackend-path = ["."]\n'
        '[project]\nname = "declared-name"\nversion = "1.0"\n',
        encoding="utf-8",
    )
    (project / "backend.py").write_text(
        """import zipfile
from pathlib import Path


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    name = "real_pkg-1.0-py3-none-any.whl"
    with zipfile.ZipFile(Path(wheel_directory) / name, "w") as archive:
        archive.writestr("real_pkg.py", "def main():\\n    print('real')\\n")
        info = "real_pkg-1.0.dist-info"
        archive.writestr(f"{info}/METADATA", "Metadata-Version: 2.1\\nName: real-pkg\\nVersion: 1.0\\n")
        archive.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\\nRoot-Is-Purelib: true\\nTag: py3-none-any\\n")
        archive.writestr(f"{info}/entry_points.txt", "[console_scripts]\\nrealapp = real_pkg:main\\n")
        archive.writestr(f"{info}/RECORD", "")
    return name
""",
        encoding="utf-8",
    )
    return project


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
def local_extras_project(copy_local_package: Callable[[str], Path]) -> Path:
    return copy_local_package("local_extras")


@pytest.fixture
def local_manpage_project(copy_local_package: Callable[[str], Path]) -> Path:
    return copy_local_package("local_manpage")


@pytest.fixture
def copy_local_package(root: Path, tmp_path: Path) -> Callable[[str], Path]:
    # a build backend may write into the project directory, so each test builds its own copy
    def copy(name: str) -> Path:
        project: Final[Path] = tmp_path / name
        shutil.copytree(root / "testdata/test_package_specifier" / name, project, ignore=_IGNORE_PROJECT_OUTPUT)
        return project

    return copy


@pytest.fixture(scope="session")
def empty_project_wheel(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_wheel(root / "testdata/empty_project", tmp_path_factory.mktemp("wheel"))


@pytest.fixture(scope="session")
def local_extras_wheel(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_wheel(root / "testdata/test_package_specifier/local_extras", tmp_path_factory.mktemp("wheel"))


@pytest.fixture(scope="session")
def local_completion_wheel(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_wheel(root / "testdata/test_package_specifier/local_completion", tmp_path_factory.mktemp("wheel"))


@pytest.fixture(scope="session")
def local_manpage_wheel(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_wheel(root / "testdata/test_package_specifier/local_manpage", tmp_path_factory.mktemp("wheel"))


def _build_wheel(project: Path, wheel_dir: Path) -> Path:
    # pip and uv build an installed directory in a fresh isolated environment, which takes seconds on Windows; tests
    # that do not exercise the source tree install this in-process build instead
    return make_wheel_in(project / "pyproject.toml", wheel_dir).file


@pytest.fixture
def copied_dependency_resource(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while building
    make_project_with_dependency: Callable[[str], Path],
    mocker: MockerFixture,
    tmp_path: Path,
) -> tuple[Path, bytes]:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    first_package: Final[Path] = _build_wheel(make_project_with_dependency("pycowsay==0.0.0.2"), tmp_path)
    exposed_app: Final[Path] = paths.CTX.bin_dir / app_name("pycowsay")
    assert not run_pipx_cli(["install", str(first_package), "--include-deps"])
    return exposed_app, exposed_app.read_bytes()


@pytest.fixture
def empty_project(root: Path, tmp_path: Path) -> Path:
    project: Final[Path] = tmp_path / "empty_project"
    shutil.copytree(root / "testdata/empty_project", project, ignore=_IGNORE_PROJECT_OUTPUT)
    return project


@pytest.fixture
def two_app_project(empty_project: Path) -> Path:
    pyproject: Final[Path] = empty_project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            "scripts.empty-project = ",
            'scripts.empty-project-extra = "empty_project.main:cli"\nscripts.empty-project = ',
        ),
        encoding="utf-8",
    )
    return empty_project


@pytest.fixture(autouse=True)
def _backend_test_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    # without the pin, a test building a Venv outside pipx_temp_env detects uv on CI's PATH and runs a real
    # `uv --version`; uv-backend tests opt back in with --backend uv
    monkeypatch.setenv("PIPX_DEFAULT_BACKEND", "pip")
    # a cached result would carry the previous test's patched shutil.which into this one
    find_uv_binary.cache_clear()
    uv_meets_minimum_version.cache_clear()
    _uv_backend_module._run_uv_version.cache_clear()  # ruff:ignore[private-member-access]  # no public cache reset
    get_backend.cache_clear()
    reset_backend_override_warnings()


@pytest.fixture(autouse=True)
def _block_external_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    # a test reaching the internet flakes on someone else's rate limit: a 403 from github.com once left an unclosed
    # SSLSocket whose ResourceWarning the GC pinned on whichever test ran next; the local pypiserver is on loopback, and
    # --net-pypiserver and --all-packages want real indexes
    if request.config.option.net_pypiserver or request.config.option.all_packages:
        return
    connect: Final = socket.socket.connect

    def guarded_connect(self: socket.socket, address: tuple[str | int, ...] | str | bytes) -> None:
        if isinstance(address, tuple) and not _is_loopback(str(address[0])):
            msg = f"test connected to {address[0]}; mock the remote instead of reaching it"
            raise RuntimeError(msg)
        connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:  # a hostname other than localhost, which may resolve anywhere
        return False


@pytest.fixture(autouse=True, scope="session")
def _resolve_lazy_imports() -> None:
    # mock.patch reads the original from the module __dict__, where an unresolved lazy import (PEP 810) is still a
    # proxy that autospec turns into a non-callable mock, so whether a test hit that depended on the tests before it
    if (lazy_type := getattr(types, "LazyImportType", None)) is None:
        return
    for module_info in pkgutil.walk_packages(pipx.__path__, "pipx."):
        importlib.import_module(module_info.name)
    for module in [module for name, module in sys.modules.items() if name == "pipx" or name.startswith("pipx.")]:
        for name, value in list(vars(module).items()):
            if type(value) is lazy_type:
                getattr(module, name)


@pytest.fixture(autouse=True)
def _isolate_pipx_paths(tmp_path: Path) -> Iterator[None]:
    # a test that skips pipx_temp_env, or whose patch misses (as one did under 3.15 lazy imports), would otherwise write
    # logs, cached venvs and shared libs into the developer's pipx home; tests resolving the defaults themselves clear
    # these overrides in a scoped monkeypatch
    with pytest.MonkeyPatch.context() as scoped:
        for name, location in (
            ("OVERRIDE_PIPX_HOME", "subdir/pipxhome"),
            ("OVERRIDE_PIPX_BIN_DIR", "otherdir/pipxbindir"),
            ("OVERRIDE_PIPX_MAN_DIR", "otherdir/pipxmandir"),
            ("OVERRIDE_PIPX_COMPLETION_DIR", "otherdir/pipxcompletiondir"),
            ("OVERRIDE_PIPX_GLOBAL_HOME", "global/pipxhome"),
            ("OVERRIDE_PIPX_GLOBAL_BIN_DIR", "global_otherdir/pipxbindir"),
            ("OVERRIDE_PIPX_GLOBAL_MAN_DIR", "global_otherdir/pipxmandir"),
            ("OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR", "global_otherdir/pipxcompletiondir"),
        ):
            scoped.setattr(paths, name, tmp_path / location)
        # where pipx logs when the pipx home refuses a log file; resolved per call, so it needs its own redirect
        scoped.setattr(platformdirs, "user_log_path", lambda *_args, **_kwargs: tmp_path / "fallback_logs")
        paths.CTX.make_local()
        yield


@pytest.fixture(autouse=True)
def _isolate_pipx_logging() -> Iterator[None]:
    yield
    # _setup_logging binds a StreamHandler to the sys.stderr of its time, and pytest swaps that stream per test, so a
    # handler left by an earlier verbose run writes to a stale stream; on a Windows cp1252 console that crashes
    # ("--- Logging error ---") once a later test logs a non-ASCII record
    pipx_logger: Final[logging.Logger] = logging.getLogger("pipx")
    for handler in pipx_logger.handlers[:]:
        pipx_logger.removeHandler(handler)
        handler.close()


@pytest.fixture(scope="session")
def standalone_python_build(tmp_path_factory: pytest.TempPathFactory) -> tuple[bytes, str]:
    # a local python-build-standalone archive in the upstream layout, so tests run the real download, unpack and
    # install code against a working interpreter; on POSIX bin/python3 is a shim that execs the running interpreter,
    # since a copied binary breaks its relative dylib/RPATH lookups on some builds, and on Windows it is the venv
    # launcher beside pyvenv.cfg, the relocatable pair Windows venvs ship
    env_dir: Final[Path] = tmp_path_factory.mktemp("standalone_python") / "python"
    if WIN:
        EnvBuilder(with_pip=False).create(env_dir)
        for launcher in (env_dir / "Scripts").glob("*.exe"):
            shutil.copy2(launcher, env_dir / launcher.name)
    else:
        (env_dir / "bin").mkdir(parents=True)
        (shim := env_dir / "bin" / "python3").write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    buffer: Final = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(env_dir, arcname="python")
    return buffer.getvalue(), ".".join(map(str, sys.version_info[:3]))


@pytest.fixture(scope="session")
def standalone_python_index(standalone_python_build: tuple[bytes, str]) -> Callable[[str], dict[str, object]]:
    archive_bytes, _ = standalone_python_build
    digest: Final[str] = f"sha256:{hashlib.sha256(archive_bytes).hexdigest()}"

    def build(full_version: str) -> dict[str, object]:
        suffixes: Final[list[str]] = [
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
    index: Final = standalone_python_index(full_version)
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda **_kwargs: index)
    monkeypatch.setattr(standalone_python, "urlopen", lambda *_args, **_kwargs: io.BytesIO(archive_bytes))


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
    markexpr: Final[str] = getattr(config.option, "markexpr", "")
    if config.option.all_packages:
        config.option.markexpr = (f"{markexpr} or " if markexpr else "") + "all_packages"
    else:
        config.option.markexpr = (f"{markexpr} and " if markexpr else "") + "not all_packages"


@pytest.fixture(scope="session", autouse=True)
def pipx_local_pypiserver(
    request: pytest.FixtureRequest, root: Path, package_cache_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    if request.config.option.net_pypiserver:
        yield ""  # tests use the real index, so there is no local URL to hand out
        return

    update_cache: Final[list[str]] = [sys.executable, "scripts/update_package_cache.py"]
    cache_paths: Final[list[str]] = ["testdata/tests_packages", str(package_cache_dir.parent)]
    # every xdist worker runs this fixture; without the lock they write the list and cache concurrently
    with FileLock(package_cache_dir.parent.with_suffix(".lock")):
        if subprocess.run([*update_cache, "--check-only", *cache_paths], check=False, cwd=root).returncode:
            subprocess.run([*update_cache, *cache_paths], check=True, cwd=root)

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("", 0))
        port: Final[int] = sock.getsockname()[1]
    os.environ["NO_PROXY"] = "127.0.0.1"
    pypiserver_process: Final = subprocess.Popen(
        [
            str(Path(sys.executable).parent / "pypi-server"),
            "run",
            "--verbose",
            "--disable-fallback",
            "--backend",
            "simple-dir",
            "--cache-control=3600",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-file",
            str(tmp_path_factory.mktemp("log") / "pypiserver.log"),
            str(package_cache_dir),
        ],
        cwd=root,
    )
    try:
        while not _accepts_connections(port):
            if pypiserver_process.poll() is not None:
                pytest.fail(f"pypiserver exited with {pypiserver_process.returncode} before listening on {port}")
            time.sleep(0.05)
        # 127.0.0.1, not localhost: localhost made Windows runs far slower, likely from IPv6/IPv4 fallback timeouts
        url: Final[str] = f"http://127.0.0.1:{port}/simple/"
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


def _accepts_connections(port: int) -> bool:
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=1)
    except OSError:
        return False
    with closing(sock):
        # while nothing listens, the OS may hand the client the target port as its own source port, so it connects
        # to itself, reads its own request back, and holds the port the server still has to bind
        return sock.getsockname() != sock.getpeername()


@pytest.fixture(scope="session")
def pipx_session_shared_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("session_shareddir")


@pytest.fixture(scope="session")
def utils_path_dirs(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    # one directory of symlinks keeps whatever else lives beside git and uv off PATH, which the ⚠️ and WARNING
    # assertions in test_install depend on; an unelevated Windows user without Developer Mode cannot create symlinks,
    # so uv gets copied, while git falls back to its own directory: git.exe finds its helpers and DLLs relative to its
    # image path, so it only runs from where it was installed
    link_dir: Final[Path] = tmp_path_factory.mktemp("session_utilstempdir")
    path_dirs: Final[list[Path]] = [link_dir]

    git: Final = shutil.which("git")
    assert git is not None, "git must be on PATH to run the test suite"
    git_path: Final[Path] = Path(git)
    try:
        (link_dir / git_path.name).symlink_to(git_path)
    except OSError:  # no symlink privilege, e.g. Windows raises WinError 1314
        path_dirs.append(git_path.parent)

    if uv := shutil.which("uv"):  # exposed only when present so the uv-backend smoke test can find it
        exposed: Final[Path] = link_dir / Path(uv).name
        try:
            exposed.symlink_to(uv)
        except OSError:
            # uv is standalone, so a copy runs the same and keeps its directory, often ~/.local/bin, off PATH
            shutil.copy2(uv, exposed)

    return path_dirs


@pytest.fixture
def pipx_temp_env(
    monkeypatch: pytest.MonkeyPatch,
    pipx_session_shared_dir: Path,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    *,
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    # shared libs are built once per session, every other pipx directory once per test
    _activate_temp_env(pipx_session_shared_dir, monkeypatch, request, utils_path_dirs, pypi=pipx_local_pypiserver)
    yield
    monkeypatch.undo()
    paths.CTX.make_local()


@pytest.fixture
def installed_pycowsay(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    capsys: pytest.CaptureFixture[str],
) -> Path:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    return paths.CTX.venvs / "pycowsay"


@pytest.fixture
def pipx_ultra_temp_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    pipx_local_pypiserver: str,
) -> Iterator[None]:
    # every test starts as if pipx had never run, shared libs included
    _activate_temp_env(tmp_path / "shareddir", monkeypatch, request, utils_path_dirs, pypi=pipx_local_pypiserver)
    yield
    monkeypatch.undo()
    paths.CTX.make_local()


def _activate_temp_env(
    pipx_shared_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    utils_path_dirs: list[Path],
    *,
    pypi: str,
) -> None:
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_SHARED_LIBS", pipx_shared_dir)
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_SHARED_LIBS", pipx_shared_dir)
    paths.CTX.make_local()  # paths.CTX reads the overrides only here

    # each importer binds SHARED_LIBS at import time, so each one gets the fresh instance
    fresh_shared_libs: Final = shared_libs._SharedLibs()  # ruff:ignore[private-member-access]  # no public factory
    # importers before the module: monkeypatch reads the old value, which on 3.15 resolves their lazy import, and
    # resolving it after the module is patched would make teardown restore the fresh instance, not the original;
    # import_module, since the re-exported upgrade function shadows the submodule on pipx.commands
    for module in (venv, _pip_backend_module, importlib.import_module("pipx.commands.upgrade"), shared_libs):
        monkeypatch.setattr(module, "SHARED_LIBS", fresh_shared_libs)

    if "PIPX_DEFAULT_PYTHON" in os.environ:
        monkeypatch.delenv("PIPX_DEFAULT_PYTHON")
    get_default_python.cache_clear()

    # macOS needs /usr/bin on PATH to compile some packages, yet apps there (ansible on GitHub runners) trigger the
    # warnings test_install.py fails on, so PATH_ORIG keeps the full PATH for the tests that need it
    monkeypatch.setenv("PATH_ORIG", f"{paths.CTX.bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("PATH_TEST", str(paths.CTX.bin_dir))
    monkeypatch.setenv("PATH", os.pathsep.join(str(entry) for entry in (paths.CTX.bin_dir, *utils_path_dirs)))
    if WIN:
        # Windows tests take the copying path even when running elevated, where symlinks would work
        symlink_cache: Final = common._CAN_SYMLINK_CACHE  # ruff:ignore[private-member-access]  # no public seeding API
        monkeypatch.setitem(symlink_cache, paths.CTX.bin_dir, False)
        monkeypatch.setitem(symlink_cache, paths.CTX.man_dir, False)
    if not request.config.option.net_pypiserver:
        monkeypatch.setenv("PIP_INDEX_URL", pypi)
        monkeypatch.setenv("UV_INDEX_URL", pypi)  # uv ignores PIP_INDEX_URL, so uv-backend tests would reach PyPI


@pytest.fixture
def permissive_umask() -> Iterator[None]:
    previous: Final[int] = os.umask(0o022)
    yield
    os.umask(previous)


@pytest.fixture
def age_shared_pip() -> Iterator[Callable[[float], float]]:
    # the pip lives in the session's shared libs: left stale, the next pipx install on this worker would upgrade it with
    # whatever pip arguments that test passes, so the original time goes back afterwards
    originals: Final[dict[Path, int]] = {}

    def age(age_sec: float) -> float:
        pip_path: Final[Path] = shared_libs.SHARED_LIBS.pip_path
        originals.setdefault(pip_path, pip_path.stat().st_mtime_ns)
        last_upgrade: Final[float] = time.time() - age_sec
        os.utime(pip_path, (last_upgrade, last_upgrade))
        shared_libs.SHARED_LIBS.has_been_updated_this_run = False
        # filesystems round timestamps, so return the stored value for exact comparison
        return pip_path.stat().st_mtime

    yield age
    for pip_path, mtime_ns in originals.items():
        os.utime(pip_path, ns=(mtime_ns, mtime_ns))


@pytest.fixture
def site_packages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (site_packages := tmp_path / "site-packages").mkdir()
    monkeypatch.setattr(
        "pipx.venv_inspect.fetch_info_in_venv", lambda _venv_python: ([str(site_packages)], {}, "Python 3.13.0")
    )
    return site_packages


@pytest.fixture
def run_from_venv(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[Path], None]]:
    # stands in for pipx changing itself: the interpreter runs from the venv and has loaded a package from it
    def activate(venv_dir: Path) -> None:
        write_import_probe(venv_dir, "old")
        monkeypatch.syspath_prepend(str(venv_dir))
        monkeypatch.setattr(sys, "prefix", str(venv_dir))
        importlib.import_module("running_probe")

    yield activate
    for name in ("running_probe", "running_probe.late"):
        sys.modules.pop(name, None)
