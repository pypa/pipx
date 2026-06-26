from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import pytest

from pipx.util import rmdir, run_subprocess

if TYPE_CHECKING:
    from pathlib import Path


def test_rmdir_without_safe_rm_is_non_fatal_for_locked_files(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    (trash_dir / "locked.dll").write_text("locked")

    def fake_rmtree(path: Path, ignore_errors: bool = False) -> None:
        assert path == trash_dir
        if not ignore_errors:
            raise PermissionError("locked file")

    monkeypatch.setattr("pipx.util.shutil.rmtree", fake_rmtree)

    with caplog.at_level(logging.WARNING, logger="pipx.util"):
        rmdir(trash_dir, safe_rm=False)

    assert trash_dir.is_dir()
    assert f"Failed to delete {trash_dir}. You may need to delete it manually." in caplog.text


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, "subprocess", id="defaults_to_subprocess"),
        pytest.param("import", "import", id="preserves_explicit"),
    ],
)
def test_subprocess_keyring_provider(monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected: str) -> None:
    if env_value is not None:
        monkeypatch.setenv("PIP_KEYRING_PROVIDER", env_value)
    else:
        monkeypatch.delenv("PIP_KEYRING_PROVIDER", raising=False)

    result = run_subprocess([sys.executable, "-c", "import os; print(os.environ['PIP_KEYRING_PROVIDER'])"])

    assert result.stdout.strip() == expected


def test_subprocess_pythonsafepath_set_for_python_commands() -> None:
    """Test that PYTHONSAFEPATH is set for Python subprocess calls to prevent CWD shadowing (issue #1575)."""
    result = run_subprocess(
        [sys.executable, "-c", "import os, sys; sys.stdout.write(os.environ.get('PYTHONSAFEPATH', ''))"]
    )

    assert result.stdout == "1"
