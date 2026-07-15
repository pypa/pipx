from __future__ import annotations

import pytest

from pipx import paths
from pipx.commands.transaction import preserve_venv
from pipx.util import PipxError


def test_preserve_venv_keeps_the_backup_out_of_the_venv_namespace(pipx_temp_env: None) -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    with preserve_venv(venv_dir, enabled=True):
        siblings = {path.name for path in paths.ctx.venvs.iterdir() if path.is_dir()}
        backups = [path for path in paths.ctx.trash.iterdir() if path.is_dir()]

    assert (siblings, len(backups)) == ({"demo"}, 1)


def test_preserve_venv_restores_the_backup_on_failure(pipx_temp_env: None) -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True):
        (venv_dir / "marker").write_text("v2", encoding="utf-8")
        raise PipxError("boom")

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"
