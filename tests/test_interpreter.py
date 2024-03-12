import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest  # type: ignore

import pipx.interpreter
import pipx.paths
import pipx.standalone_python
from pipx.constants import WINDOWS
from pipx.interpreter import (
    InterpreterResolutionError,
    _find_default_windows_python,
    _get_absolute_python_interpreter,
    find_python_interpreter,
)
from pipx.util import PipxError


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Looks for Python.exe")
@pytest.mark.parametrize("venv", [True, False])
def test_windows_python_with_version(monkeypatch, venv):
    def which(name):
        return "py"

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
        return "py"

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
        return "py"

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


def test_bad_env_python(monkeypatch):
    with pytest.raises(PipxError):
        _get_absolute_python_interpreter("bad_python")


def test_good_env_python(monkeypatch, capsys):
    good_exec = _get_absolute_python_interpreter(sys.executable)
    assert good_exec == sys.executable


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

    if target_python == "3.8":
        # 3.8 is not available in the standalone python project
        with pytest.raises(InterpreterResolutionError) as e:
            find_python_interpreter(target_python, fetch_missing_python=True)
            assert "not found" in str(e)
    else:
        python_path = find_python_interpreter(target_python, fetch_missing_python=True)
        assert python_path is not None
        assert target_python in python_path
        assert str(pipx.paths.ctx.standalone_python_cachedir) in python_path
        if WINDOWS:
            assert python_path.endswith("python.exe")
        else:
            assert python_path.endswith("python3")
        subprocess.run([python_path, "-c", "import sys; print(sys.executable)"], check=True)
