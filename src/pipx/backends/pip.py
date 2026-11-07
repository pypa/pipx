from __future__ import annotations

__lazy_modules__ = [
    "json",
    "packaging.version",
    "pipx",
    "pipx.redact",
    "pipx.shared_libs",
    "pipx.subprocess_runner",
    "pipx.trash",
    "pipx.util",
    "re",
]

import json
import logging
import re
import sys
from threading import Lock
from typing import TYPE_CHECKING, Final

from packaging.version import InvalidVersion, Version

from pipx import paths
from pipx.animate import animate
from pipx.backends._base import PIP, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.redact import redact_command_line
from pipx.shared_libs import SHARED_LIBS
from pipx.subprocess_runner import get_site_packages, run_subprocess, subprocess_post_check
from pipx.trash import safe_unlink
from pipx.util import PipxError, get_venv_paths, open_owner_only

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from re import Pattern
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
# Windows appends by seeking to the end and then writing, so fan-out tasks appending at once overwrite each other
_ERROR_LOG_LOCK: Final[Lock] = Lock()


class PipBackend(Backend):
    name = PIP

    def needs_shared_libs(self) -> bool:  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        return True

    def upgrade_packaging_libraries(self, venv_python: Path, pip_args: list[str]) -> None:
        # only venvs that ship their own pip (`pipx install pip`) reach this; shared-libs venvs upgrade through
        # shared_libs.upgrade
        self._drop_site_config(venv_python.parent.parent)
        process: Final = run_subprocess(
            [str(venv_python), "-m", "pip", "--no-input", "install", "--upgrade", *pip_args, "pip"],
            run_dir=str(venv_python.parent.parent),
        )
        subprocess_post_check(process)

    @staticmethod
    def _drop_site_config(venv_root: Path) -> None:
        # pip reads <sys.prefix>/pip.conf over the user's own configuration, and any installed wheel can unpack a data
        # file there; pip has no switch that skips only this file (--isolated still reads it, PIP_CONFIG_FILE=os.devnull
        # drops every file), so a `target` in it would make the next upgrade install outside the venv
        if (site_config := venv_root / ("pip.ini" if WINDOWS else "pip.conf")).is_file() or site_config.is_symlink():
            _LOGGER.warning(
                "Removing %s: pip would read it as configuration, and installed packages can write it. "
                "Use PIP_* variables, --pip-args or your user-level pip configuration file instead.",
                site_config,
            )
            safe_unlink(site_config)

    def create_venv(  # ruff:ignore[no-self-use, too-many-arguments]  # Backend interface method mirroring venv-creation inputs
        self,
        root: Path,
        *,
        python: str,
        venv_args: list[str],
        pip_args: list[str],
        include_pip: bool,
        verbose: bool,
    ) -> None:
        cmd: Final = [python, "-m", "venv", *([] if include_pip else ["--without-pip"]), *venv_args, str(root)]
        with animate("creating virtual environment", do_animation=not verbose):
            venv_process: Final = run_subprocess(cmd, run_dir=str(root))
        subprocess_post_check(venv_process)

        SHARED_LIBS.create(verbose=verbose, pip_args=pip_args)
        if not include_pip:
            _, python_path, _ = get_venv_paths(root)
            purelib: Final = get_site_packages(python_path)[0]
            purelib.mkdir(parents=True, exist_ok=True)
            (purelib / PIPX_SHARED_PTH).write_text("".join(f"{path}\n" for path in SHARED_LIBS.site_packages))

    def install(  # ruff:ignore[too-many-arguments]  # Backend interface method mapping flags to pip options
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        requirements: list[str],
        pip_args: list[str],
        no_deps: bool = False,
        upgrade_package: str | None = None,
        log_pip_errors: bool = True,
        verbose: bool,
    ) -> CompletedProcess[str]:
        cmd: list[str] = [str(venv_python), "-m", "pip", "--no-input", "install"]
        if upgrade_package is not None:
            cmd.append("--upgrade")
        if no_deps:
            cmd.append("--no-dependencies")
        if verbose:
            cmd.append("--progress-bar=on")
        cmd += [*pip_args, *requirements]
        self._drop_site_config(venv_root)
        process: Final = SHARED_LIBS.run_repairing_pip(
            lambda: run_subprocess(
                cmd,
                log_stdout=not log_pip_errors,
                log_stderr=not log_pip_errors,
                run_dir=str(venv_root),
                stream_output=verbose,
            ),
            pip_args=pip_args,
            verbose=verbose,
        )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process, streamed=verbose)
        return process

    def install_lock(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        lock_file: Path,
        pip_args: list[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        process: Final = SHARED_LIBS.run_repairing_pip(
            lambda: run_subprocess([str(venv_python), "-m", "pip", "--version"], run_dir=str(venv_root)),
            pip_args=pip_args,
            verbose=verbose,
        )
        try:
            version: Version | None = Version(process.stdout.split()[1])
        except (IndexError, InvalidVersion):
            version = None
        # older pip reads `--requirement pylock.toml` as a requirements file, applying its lines as options
        min_version: Final[str] = "26.1"
        if version is None or version < Version(min_version):
            msg = (
                f"Installing from {lock_file.name} needs pip>={min_version}, but this environment runs "
                f"pip {version or 'of an unknown version'}.\n"
                "Upgrade it with `pipx upgrade-shared`, or run with `--backend uv`."
            )
            raise PipxError(msg)
        return super().install_lock(
            venv_root=venv_root, venv_python=venv_python, lock_file=lock_file, pip_args=pip_args, verbose=verbose
        )

    @staticmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        return [] if not cooldown_days else ["--uploaded-prior-to", f"P{cooldown_days}D"]

    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        packages: Sequence[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        cmd: Final = [str(venv_python), "-m", "pip", "uninstall", "-y", *packages, *([] if verbose else ["-q"])]
        self._drop_site_config(venv_root)
        process: Final = SHARED_LIBS.run_repairing_pip(
            lambda: run_subprocess(cmd, run_dir=str(venv_root)), pip_args=[], verbose=verbose
        )
        subprocess_post_check(process)
        return process

    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool,
    ) -> set[str]:
        if not_required:
            from pipx.venv_inspect import list_not_required_packages  # ruff:ignore[import-outside-top-level]  # pulls in packaging.requirements, slows startup

            return list_not_required_packages(venv_python)
        cmd: Final = [str(venv_python), "-m", "pip", "list", "--format=json"]
        self._drop_site_config(venv_root)
        process: Final = SHARED_LIBS.run_repairing_pip(lambda: run_subprocess(cmd), pip_args=[], verbose=False)
        if process.returncode != 0:
            msg = (
                f"Failed to execute {process.args}.\n"
                f"Process exited with return code {process.returncode}.\n"
                f"stderr: {process.stderr}"
            )
            raise PipxError(msg)
        return {entry["name"] for entry in json.loads(process.stdout.strip())}

    def list_outdated(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        index_args: list[str],
        exclude: list[str],
    ) -> tuple[OutdatedPackage, ...]:
        self._drop_site_config(venv_root)
        process: Final = SHARED_LIBS.run_repairing_pip(
            lambda: run_subprocess(
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "list",
                    "--outdated",
                    "--format=json",
                    *index_args,
                    *(f"--exclude={name}" for name in exclude),
                ],
                run_dir=str(venv_root),
            ),
            pip_args=index_args,
            verbose=False,
        )
        return outdated_packages_from_process(process)

    def run_raw_pip(  # ruff:ignore[too-many-arguments]  # Backend interface method passing raw pip controls through
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        args: list[str],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        verbose: bool,
        in_working_dir: bool = False,
    ) -> CompletedProcess[str]:
        cmd: Final = [str(venv_python), "-m", "pip", *args, *([] if verbose else ["-q"])]
        self._drop_site_config(venv_root)
        return SHARED_LIBS.run_repairing_pip(
            lambda: run_subprocess(
                cmd,
                capture_stdout=capture_stdout,
                capture_stderr=capture_stderr,
                run_dir=None if in_working_dir else str(venv_root),
                # uncaptured, it talks to the user's terminal, as under `pipx runpip`
                interactive=not (capture_stdout or capture_stderr),
            ),
            pip_args=[],
            verbose=verbose,
        )


def subprocess_post_check_handle_pip_error(
    completed_process: CompletedProcess[str],
    tool_name: str = "pip",
    *,
    streamed: bool,
) -> None:
    if not completed_process.returncode:
        return
    _LOGGER.info("%r failed", redact_command_line(completed_process.args))
    if paths.CTX.log_file is None:
        msg = "Pipx internal error: No log_file present."
        raise PipxError(msg)
    error_file: Final[Path] = paths.CTX.log_file.parent / f"{paths.CTX.log_file.stem}_{tool_name}_errors.log"
    upper_label: Final[str] = tool_name.upper()
    # the fan-out tasks of an -all command append their failures to the same file at once
    with _ERROR_LOG_LOCK, open(error_file, "a", encoding="utf-8", opener=open_owner_only) as error_fh:
        error_fh.write(
            f"{upper_label} STDOUT\n----------\n{completed_process.stdout or ''}"
            f"\n{upper_label} STDERR\n----------\n{completed_process.stderr or ''}"
        )

    _LOGGER.error(
        "Fatal error from %s prevented installation. Full %s output in file:\n    %s", tool_name, tool_name, error_file
    )
    # the pip output analyser's patterns do not match uv's error format, so pipx shows uv's stderr as is, and either
    # tool skips its error lines once the user saw them streamed live
    if tool_name == "pip":
        _analyze_pip_output(completed_process.stdout, completed_process.stderr, streamed=streamed)
    elif not streamed and (
        uv_errors := [line for line in (completed_process.stderr or "").splitlines() if line.strip()]
    ):
        print("\nErrors from uv install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        for line in uv_errors:
            print(f"    {line}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


def _analyze_pip_output(pip_stdout: str, pip_stderr: str, *, streamed: bool) -> None:
    failed_build_stdout: list[str] = []
    last_collecting_dep: str | None = None
    # stdout carries these lines only when pip runs without -q
    for line in pip_stdout.split("\n"):
        if failed_match := re.search(r"Failed to build\s+(\S.+)$", line):
            failed_build_stdout = failed_match.group(1).strip().split()
        if collecting_match := re.search(r"^\s*Collecting\s+(\S+)", line):
            last_collecting_dep = collecting_match.group(1)

    # most useful first, each beside a pip line it catches
    relevant_searches: Final[dict[str, Pattern[str]]] = {
        # Package cairo was not found in the pkg-config search path.
        "not_found": re.compile(r"not (?:be )?found", re.IGNORECASE),
        # unable to execute 'gcc': No such file or directory
        "no_such": re.compile(r"no such", re.IGNORECASE),
        # Exception: Unable to find OpenSSL >= 1.0 headers. (Looked here: ...
        "exception_error": re.compile(r"(Exception|Error):\s*\S+"),
        # LINK : fatal error LNK1104: cannot open file 'kernel32.lib'
        "fatal_error": re.compile(r"fatal error", re.IGNORECASE),
        # ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/...
        "conflict_": re.compile(r"conflict", re.IGNORECASE),
        # error: can't copy 'lib\ansible\module_utils\ansible_release.py': doesn't exist ...
        "error_": re.compile(
            r"error:"
            r"(?!.+Command errored out)"
            r"(?!.+failed building wheel for)"
            r"(?!.+could not build wheels? for)"
            r"(?!.+failed to build one or more wheels)"
            r".+[^:]$",
            re.IGNORECASE,
        ),
    }

    relevants_saved: Final[dict[str, str]] = {}
    failed_build_stderr: Final[set[str]] = set()
    for line in pip_stderr.split("\n"):
        if failed_build_match := re.search(r"Failed to build\s+(?!one or more packages)(\S+)", line):
            failed_build_stderr.add(failed_build_match.group(1))

        for category, pattern in relevant_searches.items():
            if pattern.search(line):
                relevants_saved.setdefault(line.strip(), category)
                break

    _log_failed_builds(failed_build_stdout, failed_build_stderr, last_collecting_dep)

    if relevants_saved and not streamed:
        print("\nErrors from pip install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output

        print_categories: Final[list[str]] = list(relevant_searches)
        relevants_saved_filtered = list(relevants_saved)
        max_relevant_errors: Final[int] = 10
        while len(print_categories) > 1 and len(relevants_saved_filtered) > max_relevant_errors:
            print_categories.pop(-1)
            relevants_saved_filtered = [
                line for line, category in relevants_saved.items() if category in print_categories
            ]

        for line in relevants_saved_filtered:
            print(f"    {line}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


def _log_failed_builds(
    failed_build_stdout: list[str],
    failed_build_stderr: set[str],
    last_collecting_dep: str | None,
) -> None:
    if failed_build_stdout:
        failed_to_build_str = "\n    ".join(failed_build_stdout)
        plural_str = "s" if len(failed_build_stdout) > 1 else ""
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip failed to build package%s:\n    %s", plural_str, failed_to_build_str)
    elif failed_build_stderr:
        failed_to_build_str = "\n    ".join(failed_build_stderr)
        plural_str = "s" if len(failed_build_stderr) > 1 else ""
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip failed to build package%s:\n    %s", plural_str, failed_to_build_str)
    elif last_collecting_dep is not None:
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip failed while processing package:\n    %s", last_collecting_dep)


__all__ = [
    "PipBackend",
    "subprocess_post_check_handle_pip_error",
]
