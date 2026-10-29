from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

import pipx.interpreter
import pipx.paths
import pipx.standalone_python
from helpers import run_pipx_cli
from pipx.constants import WINDOWS, FetchPythonOptions
from pipx.interpreter import InterpreterResolutionError, find_python_interpreter
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


def test_import_defers_default_python_resolution() -> None:
    result: Final = subprocess.run(
        [sys.executable, "-c", "import pipx.interpreter; print('imported')"],
        env={**os.environ, "PIPX_DEFAULT_PYTHON": "missing-pipx-python"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode, result.stdout.strip()) == (0, "imported")


@pytest.mark.usefixtures("uncached_default_python")
def test_default_python_compatibility_attribute() -> None:
    assert pipx.interpreter.get_default_python() == pipx.interpreter.DEFAULT_PYTHON


@pytest.fixture
def uncached_default_python() -> Iterator[None]:
    pipx.interpreter.get_default_python.cache_clear()
    yield
    pipx.interpreter.get_default_python.cache_clear()


@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_resolves_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", sys.executable)

    assert pipx.interpreter.get_default_python() == str(Path(sys.executable).resolve())


def test_has_venv_leaves_venv_unimported() -> None:
    result: Final = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, pipx.interpreter; print(pipx.interpreter.has_venv(), 'venv' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode, result.stdout.strip()) == (0, "True False")


def test_has_venv_without_venv_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "venv", None)

    assert pipx.interpreter.has_venv() is False


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [pytest.param(True, id="venv"), pytest.param(False, id="no-venv")])
@pytest.mark.parametrize("prefix", [pytest.param("", id="version"), pytest.param("python", id="python-and-version")])
@pytest.mark.usefixtures("py_launcher_on_path")
def test_windows_python_with_version(monkeypatch: pytest.MonkeyPatch, venv: bool, prefix: str) -> None:
    major, minor = sys.version_info[:2]
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)

    python_path: Final[str] = find_python_interpreter(f"{prefix}{major}.{minor}", FetchPythonOptions.NEVER)

    assert f"{major}.{minor}" in python_path or f"{major}{minor}" in python_path
    assert python_path.endswith("python.exe")


@pytest.fixture
def py_launcher_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    which: Final = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name: "py" if name == "py" else which(name))


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [pytest.param(True, id="venv"), pytest.param(False, id="no-venv")])
@pytest.mark.usefixtures("py_launcher_on_path")
def test_windows_python_with_python_and_unavailable_version(monkeypatch: pytest.MonkeyPatch, venv: bool) -> None:
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)

    with pytest.raises(InterpreterResolutionError) as error:
        find_python_interpreter(
            f"python{sys.version_info.major + 99}.{sys.version_info.minor}", FetchPythonOptions.NEVER
        )

    assert "py --list" in error.value.raw_message


@pytest.mark.usefixtures("windows_default_python")
def test_windows_python_no_version_with_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: True)

    assert pipx.interpreter.get_default_python() == sys.executable


@pytest.fixture
def windows_default_python(monkeypatch: pytest.MonkeyPatch, uncached_default_python: None) -> None:  # ruff:ignore[unused-function-argument]  # the cache must be clear before and after
    monkeypatch.setattr(pipx.interpreter, "WINDOWS", True)
    monkeypatch.delenv("PIPX_DEFAULT_PYTHON", raising=False)


@pytest.mark.parametrize(
    ("found", "expected"),
    [
        pytest.param({"py": "py", "python": "python"}, "py", id="py-launcher"),
        pytest.param({"python": "python"}, "python", id="python-present"),
    ],
)
@pytest.mark.usefixtures("windows_default_python")
def test_windows_python_no_version_no_venv(
    monkeypatch: pytest.MonkeyPatch, found: dict[str, str], expected: str
) -> None:
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", found.get)

    assert pipx.interpreter.get_default_python() == expected


@pytest.mark.usefixtures("windows_default_python")
def test_windows_python_no_version_no_venv_no_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PipxError):
        pipx.interpreter.get_default_python()


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        pytest.param(9009, b"", id="stub-exit-code"),
        pytest.param(0, b"", id="no-version-printed"),
    ],
)
@pytest.mark.usefixtures("windows_store_python")
def test_windows_python_no_venv_store_stub_rejected(mocker: MockerFixture, returncode: int, stdout: bytes) -> None:
    mocker.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], returncode, stdout=stdout))

    with pytest.raises(PipxError):
        pipx.interpreter.get_default_python()


@pytest.fixture
def windows_store_python(monkeypatch: pytest.MonkeyPatch, windows_default_python: None) -> None:  # ruff:ignore[unused-function-argument]  # the store Python is looked up as the Windows default
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", {"python": "WindowsApps"}.get)


@pytest.mark.usefixtures("windows_store_python")
def test_windows_python_no_venv_store_python_that_prints_its_version(mocker: MockerFixture) -> None:
    mocker.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=b"3.8"))

    assert pipx.interpreter.get_default_python() == "WindowsApps"


@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_resolves_executable_name(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates: Final[list[str]] = [
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        f"python{sys.version_info.major}",
        "python",
    ]
    name: Final[str | None] = next((c for c in candidates if shutil.which(c)), None)
    assert name is not None, "no python executable on PATH"
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", name)

    result: Final[Path] = Path(pipx.interpreter.get_default_python())

    assert (result.is_absolute(), result.is_file()) == (True, True)


@pytest.mark.skipif(WINDOWS, reason="Unix command resolution")
@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_resolves_bare_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", f"{sys.version_info.major}.{sys.version_info.minor}")

    result: Final[Path] = Path(pipx.interpreter.get_default_python())

    assert (result.is_absolute(), result.is_file()) == (True, True)


@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_resolves_path_to_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (fake_python := tmp_path / "mypython").touch(mode=0o755)
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", str(fake_python))

    assert Path(pipx.interpreter.get_default_python()).is_absolute()


@pytest.mark.skipif(WINDOWS, reason="Windows searches the working directory for a bare command name by design")
@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_ignores_bare_name_in_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "python3").touch(mode=0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", "python3")

    assert pipx.interpreter.get_default_python() == shutil.which("python3")


@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_resolves_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "mypython").touch(mode=0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", f".{os.sep}mypython")

    assert pipx.interpreter.get_default_python() == str((tmp_path / "mypython").resolve())


@pytest.mark.parametrize(
    "python",
    [
        pytest.param("no_such_python_99.99", id="missing-name"),
        pytest.param("99.99", id="missing-version"),
    ],
)
@pytest.mark.usefixtures("uncached_default_python")
def test_get_default_python_invalid_raises(monkeypatch: pytest.MonkeyPatch, python: str) -> None:
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", python)

    with pytest.raises(InterpreterResolutionError, match="PIPX_DEFAULT_PYTHON"):
        pipx.interpreter.get_default_python()


def test_find_python_interpreter_by_path() -> None:
    assert find_python_interpreter(sys.executable, FetchPythonOptions.NEVER) == sys.executable


def test_find_python_interpreter_by_version() -> None:
    major, minor = sys.version_info[:2]
    python_path: Final[str] = find_python_interpreter(f"python{major}.{minor}", FetchPythonOptions.NEVER)
    result: Final = subprocess.run(
        [python_path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == f"{major}.{minor}"


def test_find_python_interpreter_by_name_returns_path_lookup_result(python_on_path: Path) -> None:
    assert find_python_interpreter(python_on_path.name, FetchPythonOptions.NEVER) == str(python_on_path)


@pytest.fixture
def python_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (python := tmp_path / "mypython.exe").touch(mode=0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    return python


@pytest.mark.skipif(WINDOWS, reason="Windows searches the working directory for a bare command name by design")
def test_find_python_interpreter_by_name_skips_working_directory_file(
    python_on_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cwd := tmp_path / "cwd").mkdir()
    (cwd / python_on_path.name).touch(mode=0o755)
    monkeypatch.chdir(cwd)

    assert find_python_interpreter(python_on_path.name, FetchPythonOptions.NEVER) == str(python_on_path)


@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param(f"{sys.executable}99", id="wrong-path"),
        pytest.param("1.1", id="missing-on-path"),
    ],
)
def test_find_python_interpreter_unresolvable_raises(python_version: str) -> None:
    with pytest.raises(InterpreterResolutionError):
        find_python_interpreter(python_version, FetchPythonOptions.NEVER)


@pytest.mark.parametrize(
    "fetch_python",
    [
        pytest.param(FetchPythonOptions.MISSING, id="missing"),
        pytest.param(FetchPythonOptions.ALWAYS, id="always"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_fetch_missing_python(monkeypatch: pytest.MonkeyPatch, fetch_python: FetchPythonOptions) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    target_python: Final[str] = f"{sys.version_info.major}.{sys.version_info.minor}"

    python_path: Final[str] = find_python_interpreter(target_python, fetch_python=fetch_python)

    assert target_python in python_path
    assert str(pipx.paths.CTX.standalone_python_cachedir) in python_path
    assert python_path.endswith("python.exe" if WINDOWS else "python3")
    subprocess.run([python_path, "-c", "import sys; print(sys.executable)"], check=True)


@pytest.mark.usefixtures("mocked_github_api")
def test_fetch_python_always_invalid_version_raises() -> None:
    with pytest.raises(InterpreterResolutionError, match="python-build-standalone"):
        find_python_interpreter("3.0", fetch_python=FetchPythonOptions.ALWAYS)


@pytest.mark.parametrize(
    ("system", "machine", "libc", "expected_platform"),
    [
        pytest.param("Plan9", "riscv64", "", "Plan9 on riscv64", id="system"),
        pytest.param("Linux", "aarch64", "musl", "Linux on aarch64 with musl", id="linux-libc"),
    ],
)
def test_fetch_python_unsupported_platform_raises(
    mocker: MockerFixture,
    system: str,
    machine: str,
    libc: str,
    expected_platform: str,
) -> None:
    mocker.patch.object(pipx.standalone_python.platform, "system", return_value=system)
    mocker.patch.object(pipx.standalone_python.platform, "machine", return_value=machine)
    mocker.patch.object(pipx.standalone_python.platform, "libc_ver", return_value=(libc, ""))

    with pytest.raises(InterpreterResolutionError, match="python-build-standalone") as error:
        find_python_interpreter("3.99", fetch_python=FetchPythonOptions.ALWAYS)
    assert expected_platform in str(error.value.__cause__)


def test_fetch_python_retries_incomplete_install(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch.object(pipx.standalone_python.platform, "system", return_value="Plan9")
    mocker.patch.object(pipx.standalone_python.platform, "machine", return_value="riscv64")
    (install_dir := pipx.paths.CTX.standalone_python_cachedir / "3.98").mkdir(parents=True)

    with pytest.raises(InterpreterResolutionError):
        find_python_interpreter("3.98", fetch_python=FetchPythonOptions.ALWAYS)

    assert not install_dir.exists()
    assert "A previous attempt to install python 3.98 failed. Retrying." in caplog.text


@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param("/usr/bin/python3.13", id="absolute-path"),
        pytest.param("relative/python3.13", id="relative-path"),
        pytest.param(__file__, id="existing-file"),
    ],
)
def test_fetch_python_always_rejects_paths(python_version: str) -> None:
    with pytest.raises(PipxError, match="requires a Python version"):
        find_python_interpreter(python_version, fetch_python=FetchPythonOptions.ALWAYS)


@pytest.mark.usefixtures("mocked_github_api")
@pytest.mark.parametrize(
    ("python_version", "fetch_python"),
    [
        pytest.param("..", FetchPythonOptions.ALWAYS, id="parent-always"),
        pytest.param("..", FetchPythonOptions.MISSING, id="parent-missing"),
        pytest.param(".", FetchPythonOptions.ALWAYS, id="cache-dir"),
        pytest.param("python", FetchPythonOptions.ALWAYS, id="python-stripped-to-empty"),
        pytest.param("cpython", FetchPythonOptions.MISSING, id="cpython-stripped-to-empty"),
        pytest.param(f"..{os.sep}venvs{os.sep}app", FetchPythonOptions.MISSING, id="sibling-venv"),
    ],
)
def test_fetch_python_non_version_keeps_pipx_home(
    monkeypatch: pytest.MonkeyPatch, python_version: str, fetch_python: FetchPythonOptions
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    cache_dir: Final[Path] = pipx.paths.CTX.standalone_python_cachedir
    kept: Final[list[Path]] = [cache_dir / "3.98", cache_dir.parent / "venvs" / "app"]
    for directory in kept:
        directory.mkdir(parents=True)

    with pytest.raises(InterpreterResolutionError, match="python-build-standalone"):
        find_python_interpreter(python_version, fetch_python=fetch_python)

    assert [directory.is_dir() for directory in kept] == [True, True]


@pytest.mark.usefixtures("mocked_github_api")
def test_fetch_python_missing_keeps_directory_named_by_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    project: Final[Path] = tmp_path_factory.mktemp("project")

    with pytest.raises(InterpreterResolutionError, match="python-build-standalone"):
        find_python_interpreter(str(project), fetch_python=FetchPythonOptions.MISSING)

    assert project.is_dir()


def test_find_python_interpreter_py_launcher_failure_without_fetch_raises(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    mocker.patch.object(
        pipx.interpreter, "find_py_launcher_python", autospec=True, side_effect=subprocess.CalledProcessError(1, ["py"])
    )

    with pytest.raises(InterpreterResolutionError, match="py launcher"):
        find_python_interpreter("3.13", fetch_python=FetchPythonOptions.NEVER)


def test_find_python_interpreter_py_launcher_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    monkeypatch.setattr(pipx.interpreter, "find_py_launcher_python", lambda version: f"/fake/python{version}")

    assert find_python_interpreter("3.13", fetch_python=FetchPythonOptions.NEVER) == "/fake/python3.13"


@pytest.mark.skipif(WINDOWS, reason="Python Launcher for Unix")
@pytest.mark.usefixtures("unix_py_launcher_on_path")
@pytest.mark.parametrize(
    "python_version",
    [
        pytest.param("3.14.8", id="micro"),
        pytest.param("python3.14.8", id="python-prefix-micro"),
        pytest.param("3.13t", id="free-threaded"),
    ],
)
def test_find_python_interpreter_skips_unix_py_launcher_for_non_selector(
    mocker: MockerFixture, python_version: str
) -> None:
    launcher: Final[MagicMock] = mocker.patch.object(subprocess, "run", autospec=True)

    with pytest.raises(InterpreterResolutionError, match="found in PATH"):
        find_python_interpreter(python_version, FetchPythonOptions.NEVER)
    launcher.assert_not_called()


@pytest.fixture
def unix_py_launcher_on_path(mocker: MockerFixture) -> None:
    mocker.patch.object(shutil, "which", side_effect=lambda name: "/usr/bin/py" if name == "py" else None)


@pytest.mark.skipif(WINDOWS, reason="Python Launcher for Unix")
@pytest.mark.usefixtures("unix_py_launcher_on_path")
def test_find_python_interpreter_asks_unix_py_launcher_for_minor_version(mocker: MockerFixture) -> None:
    mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0, stdout="/opt/python3.99/bin/python3.99\n"),
    )

    assert find_python_interpreter("3.99", FetchPythonOptions.NEVER) == "/opt/python3.99/bin/python3.99"


@pytest.mark.parametrize(
    ("subcommand", "command"),
    [
        pytest.param("list", ["interpreter", "list"], id="list"),
        pytest.param("prune", ["interpreter", "prune"], id="prune"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_interpreter_json_reports_an_empty_cache(
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
    command: str,
) -> None:
    assert not run_pipx_cli(["interpreter", subcommand, "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": command,
        "data": {"interpreters": [], "removed": [], "upgraded": []},
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


@pytest.mark.parametrize("subcommand", [pytest.param("list", id="list"), pytest.param("prune", id="prune")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_interpreter_quiet_says_nothing(
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
) -> None:
    assert not run_pipx_cli(["interpreter", subcommand, "--quiet"])

    captured: Final = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
