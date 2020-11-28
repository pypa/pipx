import logging
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from pipx.animate import show_cursor
from pipx.constants import WINDOWS


class PipxError(Exception):
    pass


def rmdir(path: Path) -> None:
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


def run_pypackage_bin(bin_path: Path, args: List[str]) -> None:
    def _get_env() -> Dict[str, str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.pathsep.join(
            [".", str(bin_path.parent.parent)]
            + os.getenv("PYTHONPATH", "").split(os.path.pathsep)
        )
        return env

    exec_app([str(bin_path.resolve())] + args, env=_get_env())


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


def _fix_subprocess_env(env: Dict[str, str]) -> Dict[str, str]:
    # Remove PYTHONPATH because some platforms (macOS with Homebrew) add pipx
    #   directories to it, and can make it appear to venvs as though pipx
    #   dependencies are in the venv path (#233)
    # Remove __PYVENV_LAUNCHER__ because it can cause the wrong python binary
    #   to be used (#334)
    env_blocklist = ["PYTHONPATH", "__PYVENV_LAUNCHER__"]
    for env_to_remove in env_blocklist:
        env.pop(env_to_remove, None)

    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    # Make sure that Python writes output in UTF-8
    env["PYTHONIOENCODING"] = "utf-8"
    # Make sure we install package to venv, not userbase dir
    env["PIP_USER"] = "0"
    return env


def run_subprocess(
    cmd: Sequence[Union[str, Path]],
    capture_stdout: bool = True,
    capture_stderr: bool = True,
    log_cmd_str: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run arbitrary command as subprocess, capturing stderr and stout"""
    env = dict(os.environ)
    env = _fix_subprocess_env(env)

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


def run_verify(cmd: Sequence[Union[str, Path]]) -> None:
    """Run arbitrary command as subprocess, raise PipxError if error exit code"""

    returncode = run_subprocess(
        cmd, capture_stdout=False, capture_stderr=False
    ).returncode

    if returncode:
        cmd_str = " ".join(str(c) for c in cmd)
        raise PipxError(f"{cmd_str!r} failed")


def exec_app(cmd: Sequence[Union[str, Path]], env: Dict[str, str] = None) -> None:
    """Run command, do not return

    POSIX: replace current processs with command using os.exec*()
    Windows: Use subprocess and sys.exit() to run command
    """

    if env is None:
        env = dict(os.environ)
    env = _fix_subprocess_env(env)

    # make sure we show cursor again before handing over control
    show_cursor()
    sys.stderr.flush()

    logging.info("exec_app: " + " ".join([str(c) for c in cmd]))

    if WINDOWS:
        sys.exit(
            subprocess.run(
                cmd,
                env=env,
                stdout=None,
                stderr=None,
                encoding="utf-8",
                universal_newlines=True,
            ).returncode
        )
    else:
        os.execvpe(str(cmd[0]), [str(x) for x in cmd], env)


def full_package_description(package: str, package_spec: str) -> str:
    if package == package_spec:
        return package
    else:
        return f"{package} from spec {package_spec!r}"


def wrap(
    text: str, subsequent_indent: str = "    ", keep_newlines: bool = False
) -> str:
    minimum_width = 40
    width = max(shutil.get_terminal_size((80, 40)).columns, minimum_width) - 2

    text = textwrap.dedent(text).strip()
    if keep_newlines:
        return "\n".join(
            [
                textwrap.fill(line, width=width, subsequent_indent=subsequent_indent)
                for line in text.splitlines()
            ]
        )
    else:
        return textwrap.fill(text, width=width, subsequent_indent=subsequent_indent)
