import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final, NamedTuple

import pytest

from pipx.self_install import discover_self_managed_environment

_SKIP_ON_WINDOWS: Final[pytest.MarkDecorator] = pytest.mark.skipif(
    os.name == "nt", reason="Self-managed path discovery is only supported on Unix"
)


class SelfManagedInstallation(NamedTuple):
    home: Path
    bin_dir: Path
    venv: Path
    executable: Path
    source_interpreter: Path


@pytest.fixture
def self_managed_installation(tmp_path: Path) -> SelfManagedInstallation:
    home = tmp_path / "custom" / "pipx"
    venv = home / "venvs" / "pipx"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "pipx").touch(mode=0o755)
    source_interpreter = tmp_path / "python-custom"
    source_interpreter.touch(mode=0o755)
    (venv / "pipx_metadata.json").write_text(
        json.dumps(
            {
                "main_package": {"package": "pipx"},
                "source_interpreter": {"__type__": "Path", "__Path__": str(source_interpreter)},
            }
        ),
        encoding="utf-8",
    )
    bin_dir = home / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "pipx"
    executable.symlink_to(Path("../venvs/pipx/bin/pipx"))
    return SelfManagedInstallation(home, bin_dir, venv, executable, source_interpreter)


def _get_environment_value(
    installation: SelfManagedInstallation,
    name: str,
    overrides: Mapping[str, str] | None = None,
) -> Path:
    code = (
        "import sys; "
        f"sys.prefix = {str(installation.venv)!r}; "
        f"sys.argv = [{str(installation.executable)!r}]; "
        "from pipx.commands.environment import environment; "
        f"raise SystemExit(environment({name!r}))"
    )
    env = os.environ.copy()
    for env_name in ("PIPX_HOME", "PIPX_BIN_DIR", "PIPX_DEFAULT_PYTHON"):
        env.pop(env_name, None)
    if overrides is not None:
        env.update(overrides)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    return Path(result.stdout.strip())


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    ("name", "attribute"),
    [
        ("PIPX_HOME", "home"),
        ("PIPX_BIN_DIR", "bin_dir"),
        ("PIPX_DEFAULT_PYTHON", "source_interpreter"),
    ],
    ids=["home", "bin-dir", "default-python"],
)
def test_self_managed_value_is_discovered(
    self_managed_installation: SelfManagedInstallation,
    name: str,
    attribute: str,
) -> None:
    assert _get_environment_value(self_managed_installation, name) == getattr(self_managed_installation, attribute)


@_SKIP_ON_WINDOWS
def test_self_managed_explicit_environment_wins(self_managed_installation: SelfManagedInstallation) -> None:
    explicit_home = self_managed_installation.home.parent / "explicit"
    assert (
        _get_environment_value(
            self_managed_installation,
            "PIPX_HOME",
            {"PIPX_HOME": str(explicit_home)},
        )
        == explicit_home
    )


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    ("name", "attribute"),
    [("PIPX_HOME", "home"), ("PIPX_BIN_DIR", "bin_dir")],
    ids=["home", "bin-dir"],
)
def test_self_managed_moved_value_is_discovered(
    self_managed_installation: SelfManagedInstallation,
    name: str,
    attribute: str,
) -> None:
    moved_home = self_managed_installation.home.parent.parent / "moved"
    self_managed_installation.home.rename(moved_home)
    moved_installation = self_managed_installation._replace(
        home=moved_home,
        bin_dir=moved_home / "bin",
        venv=moved_home / "venvs" / "pipx",
        executable=moved_home / "bin" / "pipx",
    )
    assert _get_environment_value(moved_installation, name) == getattr(moved_installation, attribute)


@_SKIP_ON_WINDOWS
def test_self_managed_direct_venv_script_does_not_set_bin_dir(
    self_managed_installation: SelfManagedInstallation,
) -> None:
    environment = discover_self_managed_environment(
        prefix=self_managed_installation.venv,
        executable=str(self_managed_installation.venv / "bin" / "pipx"),
    )
    assert "PIPX_BIN_DIR" not in environment


@_SKIP_ON_WINDOWS
def test_self_managed_executable_on_path_sets_bin_dir(
    self_managed_installation: SelfManagedInstallation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", f"{self_managed_installation.bin_dir}{os.pathsep}{os.environ['PATH']}")
    environment = discover_self_managed_environment(prefix=self_managed_installation.venv, executable="pipx")
    assert environment["PIPX_BIN_DIR"] == str(self_managed_installation.bin_dir)


@_SKIP_ON_WINDOWS
def test_self_managed_missing_executable_does_not_set_bin_dir(
    self_managed_installation: SelfManagedInstallation,
) -> None:
    environment = discover_self_managed_environment(
        prefix=self_managed_installation.venv,
        executable="pipx-command-that-does-not-exist",
    )
    assert "PIPX_BIN_DIR" not in environment


def test_self_managed_windows_is_ignored(
    self_managed_installation: SelfManagedInstallation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "name", "nt")
    assert not discover_self_managed_environment(
        prefix=self_managed_installation.venv,
        executable=str(self_managed_installation.executable),
    )


@_SKIP_ON_WINDOWS
def test_self_managed_missing_metadata_is_ignored(tmp_path: Path) -> None:
    venv = tmp_path / "pipx" / "venvs" / "pipx"
    venv.mkdir(parents=True)
    assert not discover_self_managed_environment(prefix=venv, executable="pipx")


@_SKIP_ON_WINDOWS
@pytest.mark.parametrize(
    "metadata",
    [[], {"main_package": {"package": "black"}}],
    ids=["non-object", "different-package"],
)
def test_self_managed_invalid_metadata_is_ignored(
    self_managed_installation: SelfManagedInstallation,
    metadata: object,
) -> None:
    (self_managed_installation.venv / "pipx_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert not discover_self_managed_environment(
        prefix=self_managed_installation.venv,
        executable=str(self_managed_installation.executable),
    )
