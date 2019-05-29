import os
from pathlib import Path
import logging
import shutil
import subprocess
import sys
from typing import List, Tuple


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


if WINDOWS:

    def get_venv_paths(root: Path) -> Tuple[Path, Path, Path]:
        bin_path = root / "Scripts"
        python_path = bin_path / "python.exe"
        site_packages = root / "Lib/site-packages"
        return bin_path, python_path, site_packages


else:

    def get_venv_paths(root: Path) -> Tuple[Path, Path, Path]:
        bin_path = root / "bin"
        python_path = bin_path / "python"
        site_packages = (
            root
            / "lib"  # noqa E503
            / f"python{sys.version_info.major}.{sys.version_info.minor}"  # noqa E503
            / "site-packages"  # noqa E503
        )
        return bin_path, python_path, site_packages
