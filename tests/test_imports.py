from __future__ import annotations

import importlib
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

import pipx.commands

if TYPE_CHECKING:
    from pathlib import Path

_LAZY_MODULES_HONORED: Final[pytest.MarkDecorator] = pytest.mark.skipif(
    sys.version_info < (3, 15), reason="__lazy_modules__ (PEP 810) is honored from Python 3.15"
)


def test_importing_util_first_succeeds(root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(root / "src")}

    result = subprocess.run(
        [sys.executable, "-c", "import pipx.util; print('Success!')"],
        check=False,
        capture_output=True,
        cwd=root,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Success!\n"


@pytest.mark.parametrize(
    "module",
    [
        pytest.param("filelock", id="filelock"),
        pytest.param("logging.config", id="logging-config"),
        pytest.param("packaging.requirements", id="packaging-requirements"),
        pytest.param("importlib.metadata", id="importlib-metadata"),
        pytest.param("pipx.venv_inspect", id="venv-inspect"),
        pytest.param("zipfile", id="zipfile"),
        pytest.param("hashlib", id="hashlib"),
        pytest.param("urllib.request", id="urllib-request"),
        pytest.param("pipx.standalone_python", id="standalone-python"),
        pytest.param("pipx.commands.install", id="command-module"),
        pytest.param("json", id="json", marks=_LAZY_MODULES_HONORED),
        pytest.param("tomllib", id="tomllib", marks=_LAZY_MODULES_HONORED),
        pytest.param("concurrent.futures", id="concurrent-futures", marks=_LAZY_MODULES_HONORED),
        pytest.param("packaging.specifiers", id="packaging-specifiers", marks=_LAZY_MODULES_HONORED),
        pytest.param("pipx.package_specifier", id="package-specifier", marks=_LAZY_MODULES_HONORED),
    ],
)
def test_importing_main_defers_heavy_module(root: Path, module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import sys, pipx.main; print({module!r} in sys.modules)"],
        check=False,
        capture_output=True,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        text=True,
    )

    assert result.stdout == "False\n", result.stderr


@_LAZY_MODULES_HONORED
@pytest.mark.parametrize(
    ("module", "loaded"),
    [
        pytest.param("tempfile", False, id="third-party-import-deferred"),
        pytest.param("pipx.colors", True, id="terminal-snapshot-eager"),
    ],
)
def test_cli_startup_loads_module(root: Path, module: str, loaded: bool) -> None:
    assert (module in _startup_imports(root, [], {})) is loaded


@_LAZY_MODULES_HONORED
@pytest.mark.parametrize(
    ("options", "environment"),
    [
        pytest.param(["-X", "lazy_imports=normal"], {}, id="x-option"),
        pytest.param([], {"PYTHON_LAZY_IMPORTS": "normal"}, id="environment-variable"),
    ],
)
def test_cli_startup_keeps_lazy_imports_mode_set_by_user(
    root: Path, options: list[str], environment: dict[str, str]
) -> None:
    assert "tempfile" in _startup_imports(root, options, environment)


def _startup_imports(root: Path, options: list[str], environment: dict[str, str]) -> set[str]:
    result = subprocess.run(
        [sys.executable, *options, "-X", "importtime", "-m", "pipx", "--version"],
        check=True,
        capture_output=True,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src"), **environment},
        text=True,
    )
    return {line.rsplit("|", 1)[-1].strip() for line in result.stderr.splitlines() if line.startswith("import time:")}


def test_commands_package_resolves_reexport_from_submodule() -> None:
    assert pipx.commands.install_all is importlib.import_module("pipx.commands.install").install_all


def test_commands_package_rejects_unknown_attribute() -> None:
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        _ = pipx.commands.missing
