import shutil
import subprocess
import sys

import pytest  # type: ignore

import pipx.interpreter
from pipx.interpreter import (
    _find_default_windows_python,
    _get_absolute_python_interpreter,
)
from pipx.util import PipxError


def test_windows_python_venv_present(monkeypatch):
    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: True)
    assert _find_default_windows_python() == sys.executable


def test_windows_python_no_venv_py_present(monkeypatch):
    def which(name):
        if name == "py":
            return "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "py"


def test_windows_python_no_venv_python_present(monkeypatch):
    def which(name):
        if name == "python":
            return "python"
        # Note: returns False for "py"

    monkeypatch.setattr(pipx.interpreter, "has_venv", lambda: False)
    monkeypatch.setattr(shutil, "which", which)
    assert _find_default_windows_python() == "python"


def test_windows_python_no_venv_no_python(monkeypatch):
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
            class Ret:
                pass

            ret = Ret()
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
