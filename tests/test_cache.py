from __future__ import annotations

from typing import Final

import pytest

from helpers import run_pipx_cli
from pipx import paths


def test_cache_dir(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["cache", "dir"])

    assert capsys.readouterr().out.strip() == str(paths.ctx.venv_cache)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        pytest.param(0, "Removed 0 cached environments.\n", id="empty"),
        pytest.param(1, "Removed 1 cached environment.\n", id="one"),
        pytest.param(2, "Removed 2 cached environments.\n", id="multiple"),
    ],
)
def test_cache_purge_removes_run_environments(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    count: int,
    expected: str,
) -> None:
    cache_names: Final[tuple[str, ...]] = tuple(f"cache-{index}" for index in range(count))
    paths.ctx.venv_cache.mkdir(parents=True)
    for cache_name in cache_names:
        (paths.ctx.venv_cache / cache_name).mkdir()

    assert not run_pipx_cli(["cache", "purge"])

    assert (
        capsys.readouterr().out,
        tuple(path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()),
    ) == (expected, ())
