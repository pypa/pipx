import logging
import os
import random
import re
import shutil
import string
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Union,
)

import pipx.constants
from pipx.animate import show_cursor
from pipx.constants import PIPX_TRASH_DIR, WINDOWS

logger = logging.getLogger(__name__)


class PipxError(Exception):
    def __init__(self, message: str, wrap_message: bool = True):
        if wrap_message:
            super().__init__(pipx_wrap(message))
        else:
            super().__init__(message)


class RelevantSearch(NamedTuple):
    pattern: Pattern[str]
    category: str


def _get_trash_file(path: Path) -> Path:
    if not PIPX_TRASH_DIR.is_dir():
        PIPX_TRASH_DIR.mkdir()
    prefix = "".join(random.choices(string.ascii_lowercase, k=8))
    return PIPX_TRASH_DIR / f"{prefix}.{path.name}"


def rmdir(path: Path, safe_rm: bool = True) -> None:
    if not path.is_dir():
        return

    logger.info(f"removing directory {path}")
    try:
        if WINDOWS:
            os.system(f'rmdir /S /Q "{str(path)}"')
        else:
            shutil.rmtree(path)
    except FileNotFoundError:
        pass

    # move it to be deleted later if it still exists
    if path.is_dir():
        if safe_rm:
            logger.warning(
                f"Failed to delete {path}. Will move it to a temp folder to delete later."
            )

            path.rename(_get_trash_file(path))
        else:
            logger.warning(
                f"Failed to delete {path}. You may need to delete it manually."
            )


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    logger.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)


def safe_unlink(file: Path) -> None:
    # Windows doesn't let us delete or overwrite files that are being run
    # But it does let us rename/move it. To get around this issue, we can move
    # the file to a temporary folder (to be deleted at a later time)

    if not file.is_file():
        return
    try:
        file.unlink()
    except PermissionError:
        file.rename(_get_trash_file(file))


def get_pypackage_bin_path(binary_name: str) -> Path:
    return (
        Path("__pypackages__")
        / (str(sys.version_info.major) + "." + str(sys.version_info.minor))
        / "lib"
        / "bin"
        / binary_name
    )


def run_pypackage_bin(bin_path: Path, args: List[str]) -> NoReturn:
    exec_app(
        [str(bin_path.resolve())] + args,
        extra_python_paths=[".", str(bin_path.parent.parent)],
    )


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
) -> "subprocess.CompletedProcess[str]":
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
    completed_process: "subprocess.CompletedProcess[str]", raise_error: bool = True
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


def dedup_ordered(input_list: List[Any]) -> List[Any]:
    output_list = []
    seen = set()
    for x in input_list:
        if x[0] not in seen:
            output_list.append(x)
            seen.add(x[0])

    return output_list


def analyze_pip_output(pip_stdout: str, pip_stderr: str) -> None:
    r"""Extract useful errors from pip output of failed install

    Print the module that failed to build
    Print some of the most relevant errors from the pip output

    Example pip stderr line for each "relevant" type:
        not_found
            Package cairo was not found in the pkg-config search path.
            src/common.h:34:10: fatal error: 'stdio.h' file not found
            The headers or library files could not be found for zlib,
        no_such
            unable to execute 'gcc': No such file or directory
            build\test1.c(2): fatal error C1083: Cannot open include file: 'cpuid.h': No such file ...
        exception_error
            Exception: Unable to find OpenSSL >= 1.0 headers. (Looked here: ...
        fatal_error
            LINK : fatal error LNK1104: cannot open file 'kernel32.lib'
        conflict_
            ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/...
        error_
            error: can't copy 'lib\ansible\module_utils\ansible_release.py': doesn't exist ...
            build\test1.c(4): error C2146: syntax error: missing ';' before identifier 'x'
    """
    max_relevant_errors = 10

    failed_build_stdout: List[str] = []
    last_collecting_dep: Optional[str] = None
    # for any useful information in stdout, `pip install` must be run without
    #   the -q option
    for line in pip_stdout.split("\n"):
        failed_match = re.search(r"Failed to build\s+(\S.+)$", line)
        collecting_match = re.search(r"^\s*Collecting\s+(\S+)", line)
        if failed_match:
            failed_build_stdout = failed_match.group(1).strip().split()
        if collecting_match:
            last_collecting_dep = collecting_match.group(1)

    # In order of most useful to least useful
    relevant_searches = [
        RelevantSearch(re.compile(r"not (?:be )?found", re.I), "not_found"),
        RelevantSearch(re.compile(r"no such", re.I), "no_such"),
        RelevantSearch(re.compile(r"(Exception|Error):\s*\S+"), "exception_error"),
        RelevantSearch(re.compile(r"fatal error", re.I), "fatal_error"),
        RelevantSearch(re.compile(r"conflict", re.I), "conflict_"),
        RelevantSearch(
            re.compile(
                r"error:"
                r"(?!.+Command errored out)"
                r"(?!.+failed building wheel for)"
                r"(?!.+could not build wheels? for)"
                r"(?!.+failed to build one or more wheels)"
                r".+[^:]$",
                re.I,
            ),
            "error_",
        ),
    ]

    failed_stderr_patt = re.compile(r"Failed to build\s+(?!one or more packages)(\S+)")

    relevants_saved = []
    failed_build_stderr = set()
    for line in pip_stderr.split("\n"):
        failed_build_match = failed_stderr_patt.search(line)
        if failed_build_match:
            failed_build_stderr.add(failed_build_match.group(1))

        for relevant_search in relevant_searches:
            if relevant_search.pattern.search(line):
                relevants_saved.append((line.strip(), relevant_search.category))
                break

    if failed_build_stdout:
        failed_to_build_str = "\n    ".join(failed_build_stdout)
        plural_str = "s" if len(failed_build_stdout) > 1 else ""
        print("", file=sys.stderr)
        logger.error(
            f"pip failed to build package{plural_str}:\n    {failed_to_build_str}"
        )
    elif failed_build_stderr:
        failed_to_build_str = "\n    ".join(failed_build_stderr)
        plural_str = "s" if len(failed_build_stderr) > 1 else ""
        print("", file=sys.stderr)
        logger.error(
            f"pip seemed to fail to build package{plural_str}:\n    {failed_to_build_str}"
        )
    elif last_collecting_dep is not None:
        print("", file=sys.stderr)
        logger.error(f"pip seemed to fail to build package:\n    {last_collecting_dep}")

    relevants_saved = dedup_ordered(relevants_saved)

    if relevants_saved:
        print("\nSome possibly relevant errors from pip install:", file=sys.stderr)

        print_categories = [x.category for x in relevant_searches]
        relevants_saved_filtered = relevants_saved.copy()
        while (len(print_categories) > 1) and (
            len(relevants_saved_filtered) > max_relevant_errors
        ):
            print_categories.pop(-1)
            relevants_saved_filtered = [
                x for x in relevants_saved if x[1] in print_categories
            ]

        for relevant_saved in relevants_saved_filtered:
            print(f"    {relevant_saved[0]}", file=sys.stderr)


def subprocess_post_check_handle_pip_error(
    completed_process: "subprocess.CompletedProcess[str]",
) -> None:
    if completed_process.returncode:
        logger.info(f"{' '.join(completed_process.args)!r} failed")
        # Save STDOUT and STDERR to file in pipx/logs/
        if pipx.constants.pipx_log_file is None:
            raise PipxError("Pipx internal error: No log_file present.")
        pip_error_file = pipx.constants.pipx_log_file.parent / (
            pipx.constants.pipx_log_file.stem + "_pip_errors.log"
        )
        with pip_error_file.open("w") as pip_error_fh:
            print("PIP STDOUT", file=pip_error_fh)
            print("----------", file=pip_error_fh)
            if completed_process.stdout is not None:
                print(completed_process.stdout, file=pip_error_fh, end="")
            print("\nPIP STDERR", file=pip_error_fh)
            print("----------", file=pip_error_fh)
            if completed_process.stderr is not None:
                print(completed_process.stderr, file=pip_error_fh, end="")

        logger.error(
            "Fatal error from pip prevented installation. Full pip output in file:\n"
            f"    {pip_error_file}"
        )

        analyze_pip_output(completed_process.stdout, completed_process.stderr)


def exec_app(
    cmd: Sequence[Union[str, Path]],
    env: Optional[Dict[str, str]] = None,
    extra_python_paths: Optional[List[str]] = None,
) -> NoReturn:
    """Run command, do not return

    POSIX: replace current processs with command using os.exec*()
    Windows: Use subprocess and sys.exit() to run command
    """

    if env is None:
        env = dict(os.environ)
    env = _fix_subprocess_env(env)

    if extra_python_paths is not None:
        env["PYTHONPATH"] = os.path.pathsep.join(
            extra_python_paths
            + (
                os.getenv("PYTHONPATH", "").split(os.path.pathsep)
                if os.getenv("PYTHONPATH")
                else []
            )
        )

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


def full_package_description(package_name: str, package_spec: str) -> str:
    if package_name == package_spec:
        return package_name
    else:
        return f"{package_name} from spec {package_spec!r}"


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
