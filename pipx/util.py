import os
from pathlib import Path
import logging
import shutil
import subprocess
import sys
from typing import List, Tuple, Sequence, Union
from pipx.constants import WINDOWS


class PipxError(Exception):
    pass


def rmdir(path: Path):
    logging.info(f"removing directory {path}")
    try:
        if WINDOWS:
            os.system(f'rmdir /S /Q "{str(path)}"')
        else:
            shutil.rmtree(path)
    except FileNotFoundError:
        pass


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    logging.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)


def get_pypackage_bin_path(binary_name: str) -> Path:
    return (
        Path("__pypackages__")
        / (str(sys.version_info.major) + "." + str(sys.version_info.minor))
        / "lib"
        / "bin"
        / binary_name
    )


def run_pypackage_bin(bin_path: Path, args: List[str]) -> int:
    def _get_env():
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.pathsep.join(
            [".", str(bin_path.parent.parent)]
            + os.getenv("PYTHONPATH", "").split(os.path.pathsep)
        )
        return env

    try:
        return subprocess.run(
            [str(bin_path.resolve())] + args, env=_get_env()
        ).returncode
    except KeyboardInterrupt:
        return 1


if WINDOWS:

    def get_venv_paths(root: Path) -> Tuple[Path, Path]:
        bin_path = root / "Scripts"
        python_path = bin_path / "python.exe"
        return bin_path, python_path


else:

    def get_venv_paths(root: Path) -> Tuple[Path, Path]:
        bin_path = root / "bin"
        python_path = bin_path / "python"
        return bin_path, python_path


def get_script_output(interpreter: Path, script: str, *args) -> str:
    # Make sure that Python writes output in UTF-8
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    output = subprocess.run(
        [str(interpreter), "-c", script, *args], stdout=subprocess.PIPE, env=env
    ).stdout.decode(encoding="utf-8")
    return output


def get_site_packages(python: Path) -> Path:
    output = get_script_output(
        python, "import sysconfig; print(sysconfig.get_path('purelib'))"
    )
    return Path(output.strip())


def run(cmd: Sequence[Union[str, Path]], check=True) -> int:
    """Run arbitrary command as subprocess"""

    cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {cmd_str}")
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    returncode = subprocess.run(cmd_str_list).returncode
    if check and returncode:
        raise PipxError(f"{cmd_str!r} failed")
    return returncode
