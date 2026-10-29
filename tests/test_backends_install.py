from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

_REQUIRES_UV: Final = pytest.mark.skipif(
    shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke"
)


def test_install_pip_with_uv_backend_errors(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_pipx_cli(["install", "pip", "--backend", "uv"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "'pip' package cannot be installed or exposed via the uv backend" in captured.err


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_index_url_beats_uv_default_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pipx_local_pypiserver: str
) -> None:
    monkeypatch.setenv("UV_DEFAULT_INDEX", tmp_path.as_uri())

    assert run_pipx_cli(["install", "pycowsay", "--backend", "uv", "--index-url", pipx_local_pypiserver]) == 0


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_uninstall_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    # Asserts that a uv-built venv records ``backend="uv"``, exposes apps the
    # same way pip venvs do, and uninstalls without re-invoking uv.
    install_rc = run_pipx_cli(["install", "pycowsay", "--backend", "uv", "--python", sys.executable])
    captured = capsys.readouterr()
    assert install_rc == 0, captured.err

    metadata_file = paths.ctx.venvs / "pycowsay" / "pipx_metadata.json"
    assert metadata_file.is_file()
    assert '"backend": "uv"' in metadata_file.read_text()

    list_rc = run_pipx_cli(["list", "--short"])
    list_out = capsys.readouterr().out
    assert list_rc == 0
    assert "pycowsay" in list_out

    uninstall_rc = run_pipx_cli(["uninstall", "pycowsay"])
    assert uninstall_rc == 0
    assert not metadata_file.exists()


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_force_install_existing() -> None:
    command = ["install", "pycowsay", "--backend", "uv"]
    assert run_pipx_cli(command) == 0
    assert run_pipx_cli([*command, "--force"]) == 0


@_REQUIRES_UV
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_ignores_uv_toml_above_venv() -> None:
    # uv fails on a malformed config file it discovers, so success proves it never read the one above its cwd
    paths.ctx.venvs.mkdir(parents=True, exist_ok=True)
    (paths.ctx.venvs / "uv.toml").write_text("index-url = [\n")

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
