import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Sequence, Tuple, Union

import pipx.constants
from pipx.animate import show_cursor
from pipx.constants import WINDOWS

logger = logging.getLogger(__name__)


class PipxError(Exception):
    def __init__(self, message: str, wrap_message: bool = True):
        if wrap_message:
            super().__init__(pipx_wrap(message))
        else:
            super().__init__(message)


def rmdir(path: Path) -> None:
    logger.info(f"removing directory {path}")
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
    logger.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)


def get_pypackage_bin_path(binary_name: str) -> Path:
    return (
        Path("__pypackages__")
        / (str(sys.version_info.major) + "." + str(sys.version_info.minor))
        / "lib"
        / "bin"
        / binary_name
    )


def run_pypackage_bin(bin_path: Path, args: List[str]) -> NoReturn:
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
    log_stdout: bool = True,
    log_stderr: bool = True,
) -> subprocess.CompletedProcess:
    """Run arbitrary command as subprocess, capturing stderr and stout"""
    env = dict(os.environ)
    env = _fix_subprocess_env(env)

    if log_cmd_str is None:
        log_cmd_str = " ".join(str(c) for c in cmd)
    logger.info(f"running {log_cmd_str}")
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    completed_process = subprocess.run(
        cmd_str_list,
        env=env,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE if capture_stderr else None,
        encoding="utf-8",
        universal_newlines=True,
    )

    if capture_stdout and log_stdout:
        logger.debug(f"stdout: {completed_process.stdout}".rstrip())
    if capture_stderr and log_stderr:
        logger.debug(f"stderr: {completed_process.stderr}".rstrip())
    logger.debug(f"returncode: {completed_process.returncode}")

    return completed_process


def subprocess_post_check(
    completed_process: subprocess.CompletedProcess, raise_error: bool = True
) -> None:
    if completed_process.returncode:
        if completed_process.stdout is not None:
            print(completed_process.stdout, file=sys.stdout, end="")
        if completed_process.stderr is not None:
            print(completed_process.stderr, file=sys.stderr, end="")
        if raise_error:
            raise PipxError(
                f"{' '.join([str(x) for x in completed_process.args])!r} failed"
            )
        else:
            logger.info(f"{' '.join(completed_process.args)!r} failed")


def dedup_with_order(input_list: List[Any]) -> List[Any]:
    output_list = []
    seen = set()
    for x in input_list:
        if x not in seen:
            output_list.append(x)
            seen.add(x)

    return output_list


def analyze_pip_output(pip_stdout, pip_stderr):
    failed_lines = []
    error_lines = []
    error2_lines = []
    capital_error_lines = []
    exception_lines = []
    exception_error_lines = []
    exception_error2_lines = []
    last_collecting_dep = None

    # analyze pip output for relevant info
    for line in pip_stdout.split("\n"):
        failed_re = re.search(r"Failed to build\s+(\S+)", line)
        collecting_re = re.search(r"^\s*Collecting\s+(\S+)", line)
        if failed_re:
            failed_lines.append(line.strip())
        if collecting_re:
            last_collecting_dep = collecting_re.group(1)
    for line in pip_stderr.split("\n"):
        exception_error_re = re.search(r"(Exception|Error):", line)
        exception_error2_re = re.search(r"(Exception|Error)", line)
        error2_re = re.search(r"error:", line, re.I)
        error_re = re.search(r"^\s*(error.+)$", line, re.I)
        capital_error_re = re.search(r"Error", line)
        exception_re = re.search(r"Exception", line)
        if error_re:
            error_lines.append(line.strip())
        if error2_re:
            error2_lines.append(line.strip())
        if capital_error_re:
            capital_error_lines.append(line.strip())
        if exception_re:
            exception_lines.append(line.strip())
        if exception_error_re:
            exception_error_lines.append(line.strip())
        if exception_error2_re:
            exception_error2_lines.append(line.strip())

    failed_lines = dedup_with_order(failed_lines)
    exception_error_lines = dedup_with_order(exception_error_lines)
    exception_error2_lines = dedup_with_order(exception_error2_lines)

    if failed_lines:
        print("Notable pip errors:", file=sys.stderr)
        for failed_line in failed_lines:
            print(f"    {failed_line}", file=sys.stderr)
    elif last_collecting_dep is not None:
        print("pip seemed to fail during the build of package:", file=sys.stderr)
        print(f"    {last_collecting_dep}", file=sys.stderr)

    if exception_error_lines:
        print("Possibly relevant errors from pip install:", file=sys.stderr)
        for exception_error_line in exception_error_lines:
            print(f"    {exception_error_line}", file=sys.stderr)
    elif exception_error2_lines:
        print("Possibly relevant errors from pip install:", file=sys.stderr)
        for exception_error2_line in exception_error2_lines:
            print(f"    {exception_error2_line}", file=sys.stderr)
    # A lot of garbage here
    # elif error2_lines:
    #     print("Possibly relevant errors from pip install:", file=sys.stderr)
    #     for error2_line in error2_lines:
    #         print(f"    {error2_line}", file=sys.stderr)

    # TODO: remove this for final code
    # print("\nDEBUG:", file=sys.stderr)
    # print("\nfailed_lines:", file=sys.stderr)
    # for failed_line in failed_lines:
    #     print(f"    {failed_line}", file=sys.stderr)
    # print("\nerror_lines:", file=sys.stderr)
    # for error_line in error_lines:
    #     print(f"    {error_line}", file=sys.stderr)
    # print("\nError_lines:", file=sys.stderr)
    # for capital_error_line in capital_error_lines:
    #     print(f"    {capital_error_line}", file=sys.stderr)
    # print("\nexception_lines:", file=sys.stderr)
    # for exception_line in exception_lines:
    #     print(f"    {exception_line}", file=sys.stderr)
    # print("\nexception_error_lines:", file=sys.stderr)
    # for exception_error_line in exception_error_lines:
    #     print(f"    {exception_error_line}", file=sys.stderr)
    # print("\nlast_collecting_dep:", file=sys.stderr)
    # print(f"    {last_collecting_dep}", file=sys.stderr)


def subprocess_post_check_handle_pip_error(
    completed_process: subprocess.CompletedProcess,
) -> None:
    if completed_process.returncode:
        # Save STDOUT and STDERR to file in pipx/logs/
        if pipx.constants.pipx_log_file is None:
            raise PipxError("Pipx internal error: No log_file present.")
        pip_error_file = pipx.constants.pipx_log_file.parent / (
            pipx.constants.pipx_log_file.stem + "_pip_errors.log"
        )
        with pip_error_file.open("w") as pip_error_fh:
            print("STDOUT", file=pip_error_fh)
            if completed_process.stdout is not None:
                print(completed_process.stdout, file=pip_error_fh, end="")
            print("STDERR", file=pip_error_fh)
            if completed_process.stderr is not None:
                print(completed_process.stderr, file=pip_error_fh, end="")

        logger.error(
            "Fatal error from pip prevented installation. Full pip output in file:\n"
            f"{pip_error_file}"
        )

        analyze_pip_output(completed_process.stdout, completed_process.stderr)

        logger.info(f"{' '.join(completed_process.args)!r} failed")


def exec_app(
    cmd: Sequence[Union[str, Path]], env: Optional[Dict[str, str]] = None
) -> NoReturn:
    """Run command, do not return

    POSIX: replace current processs with command using os.exec*()
    Windows: Use subprocess and sys.exit() to run command
    """

    if env is None:
        env = dict(os.environ)
    env = _fix_subprocess_env(env)

    # make sure we show cursor again before handing over control
    show_cursor()

    logger.info("exec_app: " + " ".join([str(c) for c in cmd]))

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


def pipx_wrap(
    text: str, subsequent_indent: str = "", keep_newlines: bool = False
) -> str:
    """Dedent, strip, wrap to shell width. Don't break on hyphens, only spaces"""
    minimum_width = 40
    width = max(shutil.get_terminal_size((80, 40)).columns, minimum_width) - 2

    text = textwrap.dedent(text).strip()
    if keep_newlines:
        return "\n".join(
            [
                textwrap.fill(
                    line,
                    width=width,
                    subsequent_indent=subsequent_indent,
                    break_on_hyphens=False,
                )
                for line in text.splitlines()
            ]
        )
    else:
        return textwrap.fill(
            text,
            width=width,
            subsequent_indent=subsequent_indent,
            break_on_hyphens=False,
        )
