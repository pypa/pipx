from __future__ import annotations

import site
import sys
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path


def test_pth_file_readable_with_non_ascii_path(tmp_path: Path) -> None:
    non_ascii_path: Final[Path] = (
        tmp_path / ("àéîöü" if sys.platform == "win32" else "用户") / "pipx" / "shared" / "site-packages"
    )
    non_ascii_path.mkdir(parents=True)
    (tmp_path / "pipx_shared.pth").write_text(f"{non_ascii_path}\n")
    known_paths: Final[set[str]] = set()

    site.addpackage(str(tmp_path), "pipx_shared.pth", known_paths)

    assert str(non_ascii_path).casefold() in {path.casefold() for path in known_paths}
