from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn
from unittest.mock import Mock

import pytest

import pipx.interpreter
import pipx.paths
import pipx.standalone_python
from helpers import run_pipx_cli, skip_if_no_standalone_python
from pipx.constants import WINDOWS, FetchPythonOptions
from pipx.interpreter import (
    InterpreterResolutionError,
    _find_default_windows_python,  # ruff:ignore[import-private-name]  # private helper under test, no public alias
    _resolve_python,  # ruff:ignore[import-private-name]  # private helper under test, no public alias
    find_python_interpreter,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

original_which = shutil.which


def test_import_defers_default_python_resolution() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import pipx.interpreter; print('imported')"],
        env={**os.environ, "PIPX_DEFAULT_PYTHON": "missing-pipx-python"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode, result.stdout.strip()) == (0, "imported")


def test_default_python_compatibility_attribute() -> None:
    pipx.interpreter.get_default_python.cache_clear()
    try:
        assert pipx.interpreter.get_default_python() == pipx.interpreter.DEFAULT_PYTHON
    finally:
        pipx.interpreter.get_default_python.cache_clear()


def test_get_default_python_resolves_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    pipx.interpreter.get_default_python.cache_clear()
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", sys.executable)
    try:
        assert pipx.interpreter.get_default_python() == str(Path(sys.executable).resolve())
    finally:
        pipx.interpreter.get_default_python.cache_clear()


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [True, False])
def test_windows_python_with_version(monkeypatch: pytest.MonkeyPatch, venv: bool) -> None:
    def which(name: str) -> str | None:
        if name == "py":
            return "py"
        return original_which(name)

    major = sys.version_info.major
    minor = sys.version_info.minor
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)
    monkeypatch.setattr(shutil, "which", which)
    python_path = find_python_interpreter(f"{major}.{minor}")
    assert python_path is not None
    assert f"{major}.{minor}" in python_path or f"{major}{minor}" in python_path
    assert python_path.endswith("python.exe")


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [True, False])
def test_windows_python_with_python_and_version(monkeypatch: pytest.MonkeyPatch, venv: bool) -> None:
    def which(name: str) -> str | None:
        if name == "py":
            return "py"
        return original_which(name)

    major = sys.version_info.major
    minor = sys.version_info.minor
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)
    monkeypatch.setattr(shutil, "which", which)
    python_path = find_python_interpreter(f"python{major}.{minor}")
    assert python_path is not None
    assert f"{major}.{minor}" in python_path or f"{major}{minor}" in python_path
    assert python_path.endswith("python.exe")


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [True, False])
def test_windows_python_with_python_and_unavailable_version(monkeypatch: pytest.MonkeyPatch, venv: bool) -> None:
    def which(name: str) -> str | None:
        if name == "py":
            return "py"
        return original_which(name)

    major = sys.version_info.major + 99
    minor = sys.version_info.minor
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)
    monkeypatch.setattr(shutil, "which", which)
    with pytest.raises(InterpreterResolutionError) as e:  # ruff:ignore[pytest-raises-with-multiple-statements]  # trailing assert is dead code today; hoisting it would change behavior
        find_python_interpreter(f"python{major}.{minor}")
        assert "py --list" in str(e)


def test_windows_python_no_version_with_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: True)
    assert _find_default_windows_python() == sys.executable


def test_windows_python_no_version_no_venv_with_py(monkeypatch: pytest.MonkeyPatch) -> None:
    def which(_name: str) -> str:
        return "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "py"


def test_windows_python_no_version_no_venv_python_present(monkeypatch: pytest.MonkeyPatch) -> None:
    def which(name: str) -> str | None:
        if name == "python":
            return "python"
        return None
        # Note: returns False for "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "python"


def test_windows_python_no_version_no_venv_no_python(monkeypatch: pytest.MonkeyPatch) -> None:
    def which(_name: str) -> None:
        return None

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    with pytest.raises(PipxError):
        _find_default_windows_python()


# Test the checks for the store Python.
def test_windows_python_no_venv_store_python(monkeypatch: pytest.MonkeyPatch) -> None:
    def which(name: str) -> str | None:
        if name == "python":
            return "WindowsApps"
        return None

    class DummyRunner:
        def __init__(self, rc: int, out: str) -> None:
            self.rc = rc
            self.out = out

        def __call__(self, *_args: object, **_kw: object) -> Mock:
            ret = Mock()
            ret.returncode = self.rc
            ret.stdout = self.out
            return ret

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)

    # Store version stub gives return code 9009
    monkeypatch.setattr(subprocess, "run", DummyRunner(9009, ""))
    with pytest.raises(PipxError):
        _find_default_windows_python()

    # Even if it doesn't, it returns no output
    monkeypatch.setattr(subprocess, "run", DummyRunner(0, ""))
    with pytest.raises(PipxError):
        _find_default_windows_python()

    # If it *does* pass the tests, we use it as it's not the stub
    monkeypatch.setattr(subprocess, "run", DummyRunner(0, "3.8"))
    assert _find_default_windows_python() == "WindowsApps"


def test_resolve_python_absolute_path() -> None:
    result = _resolve_python(sys.executable)
    assert Path(result).resolve() == Path(sys.executable).resolve()


def test_resolve_python_executable_name() -> None:
    candidates = [
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        f"python{sys.version_info.major}",
        "python",
    ]
    name = next((c for c in candidates if shutil.which(c)), None)
    assert name is not None, "no python executable on PATH"
    result = _resolve_python(name)
    assert Path(result).is_absolute()
    assert Path(result).is_file()


@pytest.mark.skipif(WINDOWS, reason="Unix command resolution")
def test_resolve_python_bare_version() -> None:
    major = sys.version_info.major
    minor = sys.version_info.minor
    result = _resolve_python(f"{major}.{minor}")
    assert Path(result).is_absolute()
    assert Path(result).is_file()


def test_resolve_python_relative_path_resolves_to_absolute(tmp_path: Path) -> None:
    fake_python = tmp_path / "mypython"
    fake_python.touch(mode=0o755)
    result = _resolve_python(str(fake_python))
    assert Path(result).is_absolute()


def test_resolve_python_invalid_raises() -> None:
    with pytest.raises(InterpreterResolutionError, match="PIPX_DEFAULT_PYTHON"):
        _resolve_python("no_such_python_99.99")


def test_resolve_python_invalid_version_raises() -> None:
    with pytest.raises(InterpreterResolutionError, match="PIPX_DEFAULT_PYTHON"):
        _resolve_python("99.99")


def test_find_python_interpreter_by_path() -> None:
    interpreter_path = sys.executable
    assert interpreter_path == find_python_interpreter(interpreter_path)


def test_find_python_interpreter_by_version() -> None:
    major = sys.version_info.major
    minor = sys.version_info.minor
    python_path = find_python_interpreter(f"python{major}.{minor}")
    assert python_path == f"python{major}.{minor}" or f"Python\\{major}.{minor}" in python_path


def test_find_python_interpreter_by_wrong_path_raises() -> None:
    interpreter_path = sys.executable + "99"
    with pytest.raises(InterpreterResolutionError) as e:  # ruff:ignore[pytest-raises-with-multiple-statements]  # trailing assert is dead code today; hoisting it would change behavior
        find_python_interpreter(interpreter_path)
        assert "like a path" in str(e)


def test_find_python_interpreter_missing_on_path_raises() -> None:
    interpreter = "1.1"
    with pytest.raises(InterpreterResolutionError) as e:  # ruff:ignore[pytest-raises-with-multiple-statements]  # trailing asserts are dead code today; hoisting them would change behavior
        find_python_interpreter(interpreter)
        assert "Python Launcher" in str(e)
        assert "on your PATH" in str(e)


@pytest.mark.parametrize(
    "fetch_python",
    [
        pytest.param(FetchPythonOptions.MISSING, id="missing"),
        pytest.param(FetchPythonOptions.ALWAYS, id="always"),
    ],
)
@skip_if_no_standalone_python
@pytest.mark.usefixtures("mocked_github_api")
def test_fetch_missing_python(monkeypatch: pytest.MonkeyPatch, fetch_python: FetchPythonOptions) -> None:
    def which(_name: str) -> None:
        return None

    monkeypatch.setattr(shutil, "which", which)

    major = sys.version_info.major
    minor = sys.version_info.minor
    target_python = f"{major}.{minor}"

    python_path = find_python_interpreter(target_python, fetch_python=fetch_python)
    assert python_path is not None
    assert target_python in python_path
    assert str(pipx.paths.ctx.standalone_python_cachedir) in python_path
    if WINDOWS:
        assert python_path.endswith("python.exe")
    else:
        assert python_path.endswith("python3")
    subprocess.run([python_path, "-c", "import sys; print(sys.executable)"], check=True)


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
    install_dir = pipx.paths.ctx.standalone_python_cachedir / "3.98"
    install_dir.mkdir(parents=True)

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


def test_find_python_interpreter_py_launcher_failure_without_fetch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    def raise_called_process(*_args: object, **_kwargs: object) -> NoReturn:
        raise subprocess.CalledProcessError(1, ["py"])

    monkeypatch.setattr(pipx.interpreter, "find_py_launcher_python", raise_called_process)
    with pytest.raises(InterpreterResolutionError, match="py launcher"):
        find_python_interpreter("3.13", fetch_python=FetchPythonOptions.NEVER)


def test_find_python_interpreter_py_launcher_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    monkeypatch.setattr(pipx.interpreter, "find_py_launcher_python", lambda v: f"/fake/python{v}")
    assert find_python_interpreter("3.13", fetch_python=FetchPythonOptions.NEVER) == "/fake/python3.13"


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

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
