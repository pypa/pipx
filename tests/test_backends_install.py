from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path


def test_install_pip_with_uv_backend_errors(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_pipx_cli(["install", "pip", "--backend", "uv"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "'pip' package cannot be installed or exposed via the uv backend" in captured.err


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke")
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


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke")
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_force_install_existing() -> None:
    command = ["install", "pycowsay", "--backend", "uv"]
    assert run_pipx_cli(command) == 0
    assert run_pipx_cli([*command, "--force"]) == 0


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke")
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_ignores_uv_toml_above_venv() -> None:
    # uv fails on a malformed config file it discovers, so success proves it never read the one above its cwd
    paths.ctx.venvs.mkdir(parents=True, exist_ok=True)
    (paths.ctx.venvs / "uv.toml").write_text("index-url = [\n")

    assert run_pipx_cli(["install", "pycowsay", "--backend", "uv"]) == 0


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke")
@pytest.mark.usefixtures("pipx_temp_env")
def test_uv_backend_install_reads_user_uv_toml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # uv fails on a malformed config file it reads, so the failure proves it still loads the user's own config
    user_config = tmp_path / "xdg" / "uv" / "uv.toml"
    user_config.parent.mkdir(parents=True)
    user_config.write_text("index-url = [\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(user_config.parent.parent))

    assert (run_pipx_cli(["install", "pycowsay", "--backend", "uv"]), str(user_config) in capsys.readouterr().err) == (
        1,
        True,
    )
