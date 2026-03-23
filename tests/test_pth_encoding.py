import site
from pathlib import Path


def test_pth_file_readable_with_non_ascii_path(tmp_path: Path) -> None:
    non_ascii_path = tmp_path / "用户" / "pipx" / "shared" / "site-packages"
    non_ascii_path.mkdir(parents=True)

    pth_file = tmp_path / "pipx_shared.pth"
    pth_file.write_text(f"{non_ascii_path}\n")

    known_paths: set[str] = set()
    site.addpackage(str(tmp_path), pth_file.name, known_paths)

    assert str(non_ascii_path).casefold() in {p.casefold() for p in known_paths}
