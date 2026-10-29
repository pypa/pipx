from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from pipx.pipx_metadata_file import PIPX_INFO_FILENAME
from pipx.self_install import discover_self_managed_environment

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_SKIP_ON_WINDOWS: Final[pytest.MarkDecorator] = pytest.mark.skipif(
    os.name == "nt", reason="Self-managed path discovery is only supported on Unix"
)


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    ("name", "attribute"),
    [
        pytest.param("PIPX_HOME", "home", id="home"),
        pytest.param("PIPX_BIN_DIR", "bin_dir", id="bin-dir"),
        pytest.param("PIPX_DEFAULT_PYTHON", "source_interpreter", id="default-python"),
    ],
)
def test_self_managed_value_is_discovered(
    self_managed_installation: _SelfManagedInstallation,
    environment_value: Callable[[_SelfManagedInstallation, str, Mapping[str, str]], Path],
    name: str,
    attribute: str,
) -> None:
    assert environment_value(self_managed_installation, name, {}) == getattr(self_managed_installation, attribute)


@_SKIP_ON_WINDOWS
def test_self_managed_explicit_environment_wins(
    self_managed_installation: _SelfManagedInstallation,
    environment_value: Callable[[_SelfManagedInstallation, str, Mapping[str, str]], Path],
) -> None:
    explicit_home: Final[Path] = self_managed_installation.home.parent / "explicit"
    assert environment_value(self_managed_installation, "PIPX_HOME", {"PIPX_HOME": str(explicit_home)}) == explicit_home


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    ("name", "attribute"),
    [
        pytest.param("PIPX_HOME", "home", id="home"),
        pytest.param("PIPX_BIN_DIR", "bin_dir", id="bin-dir"),
    ],
)
def test_self_managed_moved_value_is_discovered(
    self_managed_installation: _SelfManagedInstallation,
    environment_value: Callable[[_SelfManagedInstallation, str, Mapping[str, str]], Path],
    name: str,
    attribute: str,
) -> None:
    moved_home: Final[Path] = self_managed_installation.home.parent.parent / "moved"
    self_managed_installation.home.rename(moved_home)
    moved_installation: Final[_SelfManagedInstallation] = replace(
        self_managed_installation,
        home=moved_home,
        bin_dir=moved_home / "bin",
        venv=moved_home / "venvs" / "pipx",
        executable=moved_home / "bin" / "pipx",
    )
    assert environment_value(moved_installation, name, {}) == getattr(moved_installation, attribute)


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    "venv_script",
    [
        pytest.param(lambda installation, _linked_home: installation.venv / "bin" / "pipx", id="direct"),
        pytest.param(
            lambda installation, _linked_home: installation.bin_dir / ".." / "venvs" / "pipx" / "bin" / "pipx",
            id="through-parent-directory",
        ),
        pytest.param(
            lambda _installation, linked_home: linked_home / "venvs" / "pipx" / "bin" / "pipx",
            id="through-linked-directory",
        ),
    ],
)
def test_self_managed_venv_script_does_not_set_bin_dir(
    self_managed_installation: _SelfManagedInstallation,
    linked_home: Path,
    discover: Callable[[Path, str], dict[str, str]],
    venv_script: Callable[[_SelfManagedInstallation, Path], Path],
) -> None:
    assert "PIPX_BIN_DIR" not in discover(
        self_managed_installation.venv, str(venv_script(self_managed_installation, linked_home))
    )


@_SKIP_ON_WINDOWS
def test_self_managed_linked_home_sets_bin_dir(
    self_managed_installation: _SelfManagedInstallation,
    linked_home: Path,
    discover: Callable[[Path, str], dict[str, str]],
) -> None:
    assert discover(linked_home / "venvs" / "pipx", str(self_managed_installation.executable))["PIPX_BIN_DIR"] == str(
        self_managed_installation.bin_dir
    )


@_SKIP_ON_WINDOWS
def test_self_managed_executable_on_path_sets_bin_dir(
    self_managed_installation: _SelfManagedInstallation,
    discover: Callable[[Path, str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", f"{self_managed_installation.bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert discover(self_managed_installation.venv, "pipx")["PIPX_BIN_DIR"] == str(self_managed_installation.bin_dir)


@_SKIP_ON_WINDOWS
def test_self_managed_missing_executable_does_not_set_bin_dir(
    self_managed_installation: _SelfManagedInstallation,
    discover: Callable[[Path, str], dict[str, str]],
) -> None:
    assert "PIPX_BIN_DIR" not in discover(self_managed_installation.venv, "pipx-command-that-does-not-exist")


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    "global_home",
    [
        pytest.param(lambda installation, _linked_home: installation.home, id="direct"),
        pytest.param(lambda _installation, linked_home: linked_home, id="symlink"),
    ],
)
def test_self_managed_global_home_keeps_default_paths(
    self_managed_installation: _SelfManagedInstallation,
    linked_home: Path,
    discover: Callable[[Path, str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    global_home: Callable[[_SelfManagedInstallation, Path], Path],
) -> None:
    monkeypatch.setenv("PIPX_GLOBAL_HOME", str(global_home(self_managed_installation, linked_home)))
    assert discover(self_managed_installation.venv, str(self_managed_installation.executable)) == {
        "PIPX_DEFAULT_PYTHON": str(self_managed_installation.source_interpreter)
    }


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    "recorded",
    [
        pytest.param(lambda tmp_path: tmp_path / "bootstrap" / "bin" / "python3", id="removed"),
        pytest.param(lambda _tmp_path: Path(sys.executable), id="other-interpreter"),
    ],
)
def test_self_managed_default_python_not_backing_the_venv_is_ignored(
    self_managed_installation: _SelfManagedInstallation,
    discover: Callable[[Path, str], dict[str, str]],
    tmp_path: Path,
    recorded: Callable[[Path], Path],
) -> None:
    (self_managed_installation.venv / PIPX_INFO_FILENAME).write_text(
        json.dumps({
            "main_package": {"package": "pipx"},
            "source_interpreter": {"__type__": "Path", "__Path__": str(recorded(tmp_path))},
        }),
        encoding="utf-8",
    )

    assert discover(self_managed_installation.venv, str(self_managed_installation.executable)) == {
        "PIPX_HOME": str(self_managed_installation.home),
        "PIPX_BIN_DIR": str(self_managed_installation.bin_dir),
    }


def test_self_managed_windows_is_ignored(
    self_managed_installation: _SelfManagedInstallation,
    discover: Callable[[Path, str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "name", "nt")
    assert discover(self_managed_installation.venv, str(self_managed_installation.executable)) == {}


@_SKIP_ON_WINDOWS
def test_self_managed_missing_metadata_is_ignored(
    tmp_path: Path, discover: Callable[[Path, str], dict[str, str]]
) -> None:
    (venv := tmp_path / "pipx" / "venvs" / "pipx").mkdir(parents=True)
    assert discover(venv, "pipx") == {}


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    "metadata",
    [
        pytest.param([], id="non-object"),
        pytest.param({"main_package": {"package": "black"}}, id="different-package"),
    ],
)
def test_self_managed_invalid_metadata_is_ignored(
    self_managed_installation: _SelfManagedInstallation,
    discover: Callable[[Path, str], dict[str, str]],
    metadata: list[None] | dict[str, dict[str, str]],
) -> None:
    (self_managed_installation.venv / PIPX_INFO_FILENAME).write_text(json.dumps(metadata), encoding="utf-8")
    assert discover(self_managed_installation.venv, str(self_managed_installation.executable)) == {}


@pytest.fixture
def discover(monkeypatch: pytest.MonkeyPatch) -> Callable[[Path, str], dict[str, str]]:
    def run(prefix: Path, executable: str) -> dict[str, str]:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "prefix", str(prefix))
            patch.setattr(sys, "argv", [executable])
            return discover_self_managed_environment()

    return run


@pytest.fixture
def environment_value() -> Callable[[_SelfManagedInstallation, str, Mapping[str, str]], Path]:
    def run(installation: _SelfManagedInstallation, name: str, overrides: Mapping[str, str]) -> Path:
        code: Final[str] = (
            "import sys; "
            f"sys.prefix = {str(installation.venv)!r}; "
            f"sys.argv = [{str(installation.executable)!r}]; "
            "from pipx.commands.environment import environment; "
            f"raise SystemExit(environment({name!r}))"
        )
        env: Final[dict[str, str]] = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PIPX_HOME", "PIPX_BIN_DIR", "PIPX_DEFAULT_PYTHON"}
        }
        return Path(
            subprocess.run(
                [sys.executable, "-c", code], env={**env, **overrides}, capture_output=True, text=True, check=True
            ).stdout.strip()
        )

    return run


@pytest.fixture
def linked_home(self_managed_installation: _SelfManagedInstallation, tmp_path: Path) -> Path:
    (link := tmp_path / "home-link").symlink_to(self_managed_installation.home)
    return link


@pytest.fixture
def self_managed_installation(tmp_path: Path) -> _SelfManagedInstallation:
    home: Final[Path] = tmp_path / "custom" / "pipx"
    venv: Final[Path] = home / "venvs" / "pipx"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "pipx").touch(mode=0o755)
    (source_interpreter := tmp_path / "python-custom").touch(mode=0o755)
    (venv / "bin" / "python").symlink_to(source_interpreter)
    (venv / PIPX_INFO_FILENAME).write_text(
        json.dumps({
            "main_package": {"package": "pipx"},
            "source_interpreter": {"__type__": "Path", "__Path__": str(source_interpreter)},
        }),
        encoding="utf-8",
    )
    (bin_dir := home / "bin").mkdir()
    (executable := bin_dir / "pipx").symlink_to(Path("../venvs/pipx/bin/pipx"))
    return _SelfManagedInstallation(
        home=home, bin_dir=bin_dir, venv=venv, executable=executable, source_interpreter=source_interpreter
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _SelfManagedInstallation:
    home: Path
    bin_dir: Path
    venv: Path
    executable: Path
    source_interpreter: Path
