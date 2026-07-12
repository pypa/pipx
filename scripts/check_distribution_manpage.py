import sys
import tarfile
import zipfile
from pathlib import Path

from docutils.core import publish_string


def main() -> None:
    distribution_dir = Path(sys.argv[1])
    rst = Path(sys.argv[2]).read_text(encoding="utf-8")
    generated_manpage = publish_string(
        "\n".join(line for line in rst.splitlines() if line.strip() != ":orphan:"),
        writer="manpage",
        settings_overrides={"report_level": 5},
    )
    _check_source_archive(distribution_dir, rst.encode())
    _check_wheel(distribution_dir, generated_manpage)


def _check_source_archive(distribution_dir: Path, rst: bytes) -> None:
    source_archive_path = _require_one(list(distribution_dir.glob("pipx-*.tar.gz")), "source archive", distribution_dir)
    with tarfile.open(source_archive_path) as source_archive:
        sources = [member for member in source_archive.getmembers() if member.name.endswith("/docs/man/pipx.1.rst")]
        if len(sources) != 1:
            raise SystemExit(f"Missing docs/man/pipx.1.rst from {source_archive_path.name}")
        extracted_source = source_archive.extractfile(sources[0])
        if extracted_source is None or extracted_source.read() != rst:
            raise SystemExit(f"Manpage source differs in {source_archive_path.name}")


def _require_one(paths: list[Path], description: str, distribution_dir: Path) -> Path:
    if len(paths) != 1:
        raise SystemExit(f"Expected one pipx {description} in {distribution_dir}; found {len(paths)}")
    return paths[0]


def _check_wheel(distribution_dir: Path, generated_manpage: bytes) -> None:
    wheel_path = _require_one(list(distribution_dir.glob("pipx-*.whl")), "wheel", distribution_dir)

    with zipfile.ZipFile(wheel_path) as wheel:
        manpages = [name for name in wheel.namelist() if name.endswith(".data/data/share/man/man1/pipx.1")]
        if len(manpages) != 1:
            raise SystemExit(
                f"Wheel {wheel_path.name} has no manual page at share/man/man1/pipx.1, "
                "so installers cannot place it in the target shared-data directory"
            )
        if wheel.read(manpages[0]) != generated_manpage:
            raise SystemExit(f"Manual page in {wheel_path.name} differs from generated output")


if __name__ == "__main__":
    main()
