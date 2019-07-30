import os
from pathlib import Path
import logging
import shutil
import subprocess
import sys
from typing import List, Generator


class PipxError(Exception):
    pass


try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True


def rmdir(path: Path):
    logging.info(f"removing directory {path}")
    if WINDOWS:
        os.system(f'rmdir /S /Q "{str(path)}"')
    else:
        shutil.rmtree(path)


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    logging.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)


def get_pypackage_bin_path(binary_name: str) -> Path:
    return (
        Path("__pypackages__")
        / (str(sys.version_info.major) + "." + str(sys.version_info.minor))  # noqa E503
        / "lib"  # noqa E503
        / "bin"  # noqa E503
        / binary_name  # noqa E503
    )


def run_pypackage_bin(bin_path: Path, args: List[str]) -> int:
    def _get_env():
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.pathsep.join(
            [".", str(bin_path.parent.parent)]
            + os.getenv("PYTHONPATH", "").split(os.path.pathsep)  # noqa E503
        )
        return env

    try:
        return subprocess.run(
            [str(bin_path.resolve())] + args, env=_get_env()
        ).returncode
    except KeyboardInterrupt:
        return 1


class VenvContainer:
    """A collection of venvs managed by pipx.
    """

    def __init__(self, root: Path):
        self._root = root

    def __repr__(self):
        return f"VenvContainer({str(self._root)!r})"

    def __str__(self):
        return str(self._root)

    def iter_venv_dirs(self) -> Generator[Path, None, None]:
        """Iterate venv directories in this container.
        """
        for entry in self._root.iterdir():
            if not entry.is_dir():
                continue
            yield entry

    def get_venv_dir(self, package: str) -> Path:
        """Return the expected venv path for given `package`.
        """
        return self._root.joinpath(package)


def autocomplete_list_of_installed_packages(
    venv_container: VenvContainer, *args, **kwargs
) -> List[str]:
    return list(str(p.name) for p in sorted(venv_container.iter_venv_dirs()))
