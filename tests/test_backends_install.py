from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

_REQUIRES_UV: Final[pytest.MarkDecorator] = pytest.mark.skipif(
    shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke"
)


def test_install_pip_with_uv_backend_errors(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code: Final[int] = run_pipx_cli(["install", "pip", "--backend", "uv"])

    assert (
        exit_code,
        "'pip' package cannot be installed or exposed via the uv backend" in capsys.readouterr().err,
    ) == (1, True)


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_index_url_beats_uv_default_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pipx_local_pypiserver: str
) -> None:
    monkeypatch.setenv("UV_DEFAULT_INDEX", tmp_path.as_uri())

    assert run_pipx_cli(["install", "pycowsay", "--backend", "uv", "--index-url", pipx_local_pypiserver]) == 0


@pytest.fixture
def uv_installed_pycowsay(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    capsys: pytest.CaptureFixture[str],
) -> Path:
    exit_code: Final[int] = run_pipx_cli(["install", "pycowsay", "--backend", "uv", "--python", sys.executable])
    assert exit_code == 0, capsys.readouterr().err
    return paths.CTX.venvs / "pycowsay" / "pipx_metadata.json"


@_REQUIRES_UV
def test_uv_backend_install_records_backend(uv_installed_pycowsay: Path) -> None:
    assert '"backend": "uv"' in uv_installed_pycowsay.read_text(encoding="utf-8")


@_REQUIRES_UV
@pytest.mark.usefixtures("uv_installed_pycowsay")
def test_uv_backend_install_lists_package(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code: Final[int] = run_pipx_cli(["list", "--short"])

    assert (exit_code, "pycowsay" in capsys.readouterr().out) == (0, True)


@_REQUIRES_UV
def test_uv_backend_uninstall_removes_metadata(uv_installed_pycowsay: Path) -> None:
    assert (run_pipx_cli(["uninstall", "pycowsay"]), uv_installed_pycowsay.exists()) == (0, False)


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_force_install_existing() -> None:
    command: Final[list[str]] = ["install", "pycowsay", "--backend", "uv"]
    assert run_pipx_cli(command) == 0
    assert run_pipx_cli([*command, "--force"]) == 0


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_ignores_uv_toml_above_venv() -> None:
    # uv fails on a malformed config file it discovers, so success proves it never read the one above its cwd
    paths.CTX.venvs.mkdir(parents=True, exist_ok=True)
    (paths.CTX.venvs / "uv.toml").write_text("index-url = [\n")

    assert run_pipx_cli(["install", "pycowsay", "--backend", "uv"]) == 0


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_reads_user_uv_toml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # uv fails on a malformed config file it reads, so the failure proves it still loads the user's own config
    user_config: Final[Path] = tmp_path / "xdg" / "uv" / "uv.toml"
    user_config.parent.mkdir(parents=True)
    user_config.write_text("index-url = [\n")
    # uv's user config directory is XDG_CONFIG_HOME on Unix and APPDATA on Windows
    for variable in ("XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.setenv(variable, str(user_config.parent.parent))

    assert (run_pipx_cli(["install", "pycowsay", "--backend", "uv"]), str(user_config) in capsys.readouterr().err) == (
        1,
        True,
    )
