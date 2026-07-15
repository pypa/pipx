from __future__ import annotations

import pytest

from pipx import paths
from pipx.commands.transaction import preserve_venv
from pipx.util import PipxError


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_keeps_the_backup_out_of_the_venv_namespace() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    with preserve_venv(venv_dir, enabled=True):
        siblings = {path.name for path in paths.ctx.venvs.iterdir() if path.is_dir()}
        backups = [path for path in paths.ctx.trash.iterdir() if path.is_dir()]

    assert (siblings, len(backups)) == ({"demo"}, 1)


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_restores_the_backup_on_failure() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    def corrupt_then_fail() -> None:
        (venv_dir / "marker").write_text("v2", encoding="utf-8")
        msg = "boom"
        raise PipxError(msg)

    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True):
        corrupt_then_fail()

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"
