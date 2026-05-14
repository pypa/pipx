from __future__ import annotations

import shutil
import sys

import pytest

from helpers import run_pipx_cli
from pipx import paths


def test_install_pip_with_uv_backend_errors(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_pipx_cli(["install", "pip", "--backend", "uv"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "'pip' package cannot be installed or exposed via the uv backend" in captured.err


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH; skipping uv integration smoke")
def test_uv_backend_install_uninstall_smoke(pipx_temp_env, capsys: pytest.CaptureFixture[str]) -> None:
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
