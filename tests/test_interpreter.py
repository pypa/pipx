import shutil
import sys
import pytest  # type: ignore
import pipx.interpreter
from pipx.interpreter import _find_default_windows_python
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


# TODO: We don't test the checks for the store Python.
