from __future__ import annotations

import stat
import subprocess
from functools import partial
from itertools import groupby
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS
from pipx import paths
from pipx.backends.pip import subprocess_post_check_handle_pip_error
from pipx.fanout import fan_out

if TYPE_CHECKING:
    from pathlib import Path


def test_pip_error_logs_of_concurrent_failures_stay_whole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.CTX, "log_file", tmp_path / "cmd.log")
    tags: Final[str] = "ABCDEFGH"

    def fail(tag: str) -> None:
        output: Final[str] = f"{tag * 79}\n" * 2000
        subprocess_post_check_handle_pip_error(subprocess.CompletedProcess([], 1, output, output), streamed=False)

    fan_out([partial(fail, tag) for tag in tags], sequential=False)

    lines: Final[list[str]] = (tmp_path / "cmd_pip_errors.log").read_text(encoding="utf-8").splitlines()
    blocks: Final[list[str]] = [tag for tag, _ in groupby(line[0] for line in lines if line[:1] in set(tags))]
    assert sorted(blocks) == sorted(tags)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("permissive_umask")
def test_pip_error_log_is_owner_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.CTX, "log_file", tmp_path / "cmd.log")

    subprocess_post_check_handle_pip_error(subprocess.CompletedProcess([], 1, "out", "err"), streamed=False)

    assert stat.S_IMODE((tmp_path / "cmd_pip_errors.log").stat().st_mode) == 0o600
