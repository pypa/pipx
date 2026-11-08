from __future__ import annotations

import site
from typing import TYPE_CHECKING, Final

import pytest

from harness import WIN

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "non_ascii_dir",
    [
        pytest.param("用户", id="posix", marks=pytest.mark.skipif(WIN, reason="the Windows case uses Latin letters")),
        pytest.param("àéîöü", id="windows", marks=pytest.mark.skipif(not WIN, reason="Windows only")),
    ],
)
def test_pth_file_readable_with_non_ascii_path(tmp_path: Path, non_ascii_dir: str) -> None:
    non_ascii_path: Final[Path] = tmp_path / non_ascii_dir / "pipx" / "shared" / "site-packages"
    non_ascii_path.mkdir(parents=True)
    (tmp_path / "pipx_shared.pth").write_text(f"{non_ascii_path}\n")
    known_paths: Final[set[str]] = set()

    site.addpackage(str(tmp_path), "pipx_shared.pth", known_paths)

    assert str(non_ascii_path).casefold() in {path.casefold() for path in known_paths}
