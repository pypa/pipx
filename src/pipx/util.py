import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence, Tuple, Union, Optional

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


def get_site_packages(python: Path) -> Path:
    output = run_subprocess(
        [python, "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_stderr=False,
    ).stdout
    path = Path(output.strip())
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_subprocess(
    cmd: Sequence[Union[str, Path]],
    capture_stdout: bool = True,
    capture_stderr: bool = True,
    log_cmd_str: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run arbitrary command as subprocess, capturing stderr and stout"""
    env = dict(os.environ)

    # Remove PYTHONPATH because some platforms (macOS with Homebrew) add pipx
    #   directories to it, and can make it appear to venvs as though pipx
    #   dependencies are in the venv path (#233)
    # Remove __PYVENV_LAUNCHER__ because it can cause the wrong python binary
    #   to be used (#334)
    env_blacklist = ["PYTHONPATH", "__PYVENV_LAUNCHER__"]
    for env_to_remove in env_blacklist:
        env.pop(env_to_remove, None)

    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    # Make sure that Python writes output in UTF-8
    env["PYTHONIOENCODING"] = "utf-8"

    if log_cmd_str is None:
        log_cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {log_cmd_str}")
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    return subprocess.run(
        cmd_str_list,
        env=env,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE if capture_stderr else None,
        encoding="utf-8",
        universal_newlines=True,
    )


def run(cmd: Sequence[Union[str, Path]], check=True) -> int:
    """Run arbitrary command as subprocess"""

    returncode = run_subprocess(
        cmd, capture_stdout=False, capture_stderr=False
    ).returncode

    if check and returncode:
        cmd_str = " ".join(str(c) for c in cmd)
        raise PipxError(f"{cmd_str!r} failed")
    return returncode


def valid_pypi_name(package_name: str) -> bool:
    # https://www.python.org/dev/peps/pep-0508/#names
    return bool(
        re.search(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", package_name, re.I)
    )


def full_package_description(package: str, package_spec: str) -> str:
    if package == package_spec:
        return package
    else:
        return f"{package} from spec {package_spec!r}"
