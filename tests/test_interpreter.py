import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import pipx.interpreter
import pipx.paths
import pipx.standalone_python
from pipx.constants import WINDOWS
from pipx.interpreter import (
    InterpreterResolutionError,
    _find_default_windows_python,
    _resolve_python,
    find_python_interpreter,
)
from pipx.util import PipxError

original_which = shutil.which


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [True, False])
def test_windows_python_with_version(monkeypatch, venv):
    def which(name):
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
def test_windows_python_with_python_and_version(monkeypatch, venv):
    def which(name):
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
def test_windows_python_with_python_and_unavailable_version(monkeypatch, venv):
    def which(name):
        if name == "py":
            return "py"
        return original_which(name)

    major = sys.version_info.major + 99
    minor = sys.version_info.minor
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: venv)
    monkeypatch.setattr(shutil, "which", which)
    with pytest.raises(InterpreterResolutionError) as e:
        find_python_interpreter(f"python{major}.{minor}")
        assert "py --list" in str(e)


def test_windows_python_no_version_with_venv(monkeypatch):
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: True)
    assert _find_default_windows_python() == sys.executable


def test_windows_python_no_version_no_venv_with_py(monkeypatch):
    def which(name):
        return "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "py"


def test_windows_python_no_version_no_venv_python_present(monkeypatch):
    def which(name):
        if name == "python":
            return "python"
        # Note: returns False for "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "python"


def test_windows_python_no_version_no_venv_no_python(monkeypatch):
    def which(name):
        return None

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    with pytest.raises(PipxError):
        _find_default_windows_python()


# Test the checks for the store Python.
def test_windows_python_no_venv_store_python(monkeypatch):
    def which(name):
        if name == "python":
            return "WindowsApps"

    class dummy_runner:
        def __init__(self, rc, out):
            self.rc = rc
            self.out = out

        def __call__(self, *args, **kw):
            ret = Mock()
            ret.returncode = self.rc
            ret.stdout = self.out
            return ret

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)

    # Store version stub gives return code 9009
    monkeypatch.setattr(subprocess, "run", dummy_runner(9009, ""))
    with pytest.raises(PipxError):
        _find_default_windows_python()

    # Even if it doesn't, it returns no output
    monkeypatch.setattr(subprocess, "run", dummy_runner(0, ""))
    with pytest.raises(PipxError):
        _find_default_windows_python()

    # If it *does* pass the tests, we use it as it's not the stub
    monkeypatch.setattr(subprocess, "run", dummy_runner(0, "3.8"))
    assert _find_default_windows_python() == "WindowsApps"


def test_resolve_python_absolute_path() -> None:
    result = _resolve_python(sys.executable)
    assert Path(result).resolve() == Path(sys.executable).resolve()


@pytest.mark.skipif(WINDOWS, reason="pythonX.Y is not typically on PATH on Windows")
def test_resolve_python_executable_name() -> None:
    major = sys.version_info.major
    minor = sys.version_info.minor
    name = f"python{major}.{minor}"
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


def test_find_python_interpreter_by_path(monkeypatch):
    interpreter_path = sys.executable
    assert interpreter_path == find_python_interpreter(interpreter_path)


def test_find_python_interpreter_by_version(monkeypatch):
    major = sys.version_info.major
    minor = sys.version_info.minor
    python_path = find_python_interpreter(f"python{major}.{minor}")
    assert python_path == f"python{major}.{minor}" or f"Python\\{major}.{minor}" in python_path


def test_find_python_interpreter_by_wrong_path_raises(monkeypatch):
    interpreter_path = sys.executable + "99"
    with pytest.raises(InterpreterResolutionError) as e:
        find_python_interpreter(interpreter_path)
        assert "like a path" in str(e)


def test_find_python_interpreter_missing_on_path_raises(monkeypatch):
    interpreter = "1.1"
    with pytest.raises(InterpreterResolutionError) as e:
        find_python_interpreter(interpreter)
        assert "Python Launcher" in str(e)
        assert "on your PATH" in str(e)


def test_fetch_missing_python(monkeypatch, mocked_github_api):
    def which(name):
        return None

    monkeypatch.setattr(shutil, "which", which)

    major = sys.version_info.major
    minor = sys.version_info.minor
    target_python = f"{major}.{minor}"

    python_path = find_python_interpreter(target_python, fetch_missing_python=True)
    assert python_path is not None
    assert target_python in python_path
    assert str(pipx.paths.ctx.standalone_python_cachedir) in python_path
    if WINDOWS:
        assert python_path.endswith("python.exe")
    else:
        assert python_path.endswith("python3")
    subprocess.run([python_path, "-c", "import sys; print(sys.executable)"], check=True)
