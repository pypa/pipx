import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest  # type: ignore

import pipx.interpreter
from pipx.interpreter import (
    _find_default_windows_python,
    _get_absolute_python_interpreter,
    find_py_launcher_python,
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
    python_path = find_py_launcher_python(f"{major}.{minor}")
    assert python_path is not None
    assert f"{major}.{minor}" in python_path or f"{major}{minor}" in python_path
    assert python_path.endswith("python.exe")


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
