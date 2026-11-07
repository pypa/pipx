from __future__ import annotations

__lazy_modules__ = [
    "contextlib",
    "importlib",
    "json",
    "pathlib",
    "pipx.backends.pip",
    "pipx.paths",
    "pipx.subprocess_runner",
    "pipx.trash",
    "pipx.util",
    "shutil",
    "subprocess",
]

import json
import logging
import re
import shutil
import subprocess
from contextlib import nullcontext
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.version import InvalidVersion, Version

from pipx.animate import animate
from pipx.backends._base import UV, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.backends.pip import subprocess_post_check_handle_pip_error
from pipx.constants import WINDOWS
from pipx.paths import CTX
from pipx.subprocess_runner import run_subprocess, subprocess_post_check
from pipx.trash import running_launcher_moved_aside
from pipx.util import PipxError, reject_empty_index

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
# uv lets UV_DEFAULT_INDEX override a command-line --index-url, but not --default-index
#: The uv flags that take the place of each pip index flag.
PIP_TO_UV_INDEX_FLAGS: Final[dict[str, str]] = dict.fromkeys(("--index-url", "-i"), "--default-index")


def _load_uv_bin_finder() -> Callable[[], str] | None:
    try:
        return import_module("uv").find_uv_bin
    except (AttributeError, ImportError):
        return None


_FIND_UV_BIN_FROM_EXTRA: Final[Callable[[], str] | None] = _load_uv_bin_finder()
_MIN_UV_VERSION: Final[Version] = Version("0.9.17")
# Version() validates the captured token
_VERSION_RE: Final[re.Pattern[str]] = re.compile(r"uv\s+(\S+)")


class UvBackend(Backend):
    """Backend that installs packages with ``uv pip``, into the interpreter of each environment.

    :cvar name: the name the backend is chosen by.
    """

    name = UV

    def __init__(self) -> None:
        self._binary = resolve_uv_binary()
        _, source = find_uv_binary()
        _LOGGER.info("using %s uv %s from %s", source, _check_uv_version(self._binary), self._binary)

    def needs_shared_libs(self) -> bool:  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        """Return whether environments need the shared pip libraries.

        :returns: always False, as uv environments ship no pip.
        """
        return False

    def upgrade_packaging_libraries(  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        self, venv_python: Path, pip_args: list[str]
    ) -> None:
        """Do nothing, as uv environments ship no pip to upgrade.

        :param venv_python: the interpreter of the environment.
        :param pip_args: extra arguments for the installer.
        """
        del venv_python, pip_args  # uv venvs ship no pip to upgrade

    def create_venv(  # ruff:ignore[too-many-arguments]  # Backend interface method mirroring venv-creation inputs
        self,
        root: Path,
        *,
        python: str,
        venv_args: list[str],
        pip_args: list[str],
        include_pip: bool,
        verbose: bool,
    ) -> None:
        """Create a virtual environment with uv.

        :param root: the directory of the environment.
        :param python: the interpreter to create the environment with.
        :param venv_args: extra arguments for ``uv venv``.
        :param pip_args: extra arguments for the installer, unused as uv seeds no pip.
        :param include_pip: whether the environment ships its own pip, which uv cannot do.
        :param verbose: show the progress of the creation.
        :raises PipxError: when the environment is asked to ship pip.
        """
        del pip_args  # uv venv has no pip to seed
        if include_pip:
            msg = (
                "The uv backend cannot create a virtual environment with pip preinstalled.\n"
                "Reinstall the package with `--backend pip` (or unset PIPX_DEFAULT_BACKEND)."
            )
            raise PipxError(msg)
        cmd: Final[list[str | Path]] = [
            self._binary,
            "venv",
            "--python",
            python,
            "--allow-existing",
            *venv_args,
            "--verbose" if verbose else "--quiet",
            str(root),
        ]
        with animate("creating virtual environment", do_animation=not verbose):
            process: Final = run_subprocess(cmd, run_dir=str(root), env_overrides=self._env_overrides())
        subprocess_post_check(process)

    @staticmethod
    def _env_overrides() -> dict[str, str | None]:
        # Stripping VIRTUAL_ENV stops uv from auto-targeting an active venv when no `--python` flag is passed. pipx
        # shows its own spinner in place of uv's bar, and uv hides the bar under --verbose anyway. UV_PROJECT moves
        # uv's project-config search from its working directory, which can sit in a shared /tmp, to pipx's home; user
        # and system config still load.
        return {"VIRTUAL_ENV": None, "UV_NO_PROGRESS": "1", "UV_PROJECT": str(CTX.home)}

    def install(  # ruff:ignore[too-many-arguments]  # Backend interface method mapping flags to uv options
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
        """Install requirements into an environment with ``uv pip``.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param requirements: the requirements to install, including option pairs such as ``--requirement`` and a file.
        :param pip_args: extra arguments for uv.
        :param no_deps: skip the dependencies of the requirements.
        :param upgrade_package: the package to upgrade, if any.
        :param log_pip_errors: log the output of uv when it fails.
        :param verbose: show the progress of the installation.
        :returns: the completed uv process.
        """
        reject_empty_index(pip_args)
        cmd = self._uv_pip_command("install", venv_python, verbose=verbose)
        # uv's --upgrade re-resolves every dependency, pip's only-if-needed default upgrades only the named package
        if upgrade_package is not None:
            cmd += ["--upgrade-package", upgrade_package]
        if no_deps:
            cmd.append("--no-deps")
        cmd += [*self._default_index_args(self._strip_pip_quiet_flags(pip_args)), *requirements]
        # unlike pip, which moves the files it replaces aside, uv deletes them in place, and Windows refuses that for
        # the running launcher of a pipx upgrading itself
        with running_launcher_moved_aside(venv_python.parent) if WINDOWS else nullcontext():
            process: Final = run_subprocess(
                cmd,
                run_dir=str(venv_root),
                log_stdout=not log_pip_errors,
                log_stderr=not log_pip_errors,
                env_overrides=self._env_overrides(),
                stream_output=verbose,
            )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process, tool_name="uv", streamed=verbose)
        return process

    def _uv_pip_command(self, subcommand: str, venv_python: Path, *, verbose: bool) -> list[str | Path]:
        return [self._binary, "pip", subcommand, "--python", str(venv_python), "--verbose" if verbose else "--quiet"]

    @staticmethod
    def _default_index_args(pip_args: list[str]) -> list[str]:
        return [
            f"{PIP_TO_UV_INDEX_FLAGS[flag]}{separator}{value}"
            if flag in PIP_TO_UV_INDEX_FLAGS
            else f"{PIP_TO_UV_INDEX_FLAGS['-i']}={arg[2:]}"
            if arg.startswith("-i")
            else arg
            for arg in pip_args
            for flag, separator, value in [arg.partition("=")]
        ]

    @staticmethod
    def _strip_pip_quiet_flags(pip_args: list[str]) -> list[str]:
        return [arg for arg in pip_args if arg not in {"-q", "-qq", "--quiet"}]

    @staticmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        """Return the uv arguments that exclude releases published within the last cooldown days.

        :param cooldown_days: the number of days a release must have been out, or None to skip the cooldown.
        :returns: the uv arguments.
        """
        return [] if not cooldown_days else ["--exclude-newer", f"P{cooldown_days}D"]

    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        packages: Sequence[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        """Uninstall packages from an environment with ``uv pip``.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param packages: the names of the packages to uninstall.
        :param verbose: show the output of uv.
        :returns: the completed uv process.
        """
        cmd: Final = [*self._uv_pip_command("uninstall", venv_python, verbose=verbose), *packages]
        process: Final = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=self._env_overrides())
        subprocess_post_check(process)
        return process

    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool,
    ) -> set[str]:
        """Return the names of the packages installed in an environment.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param not_required: return only the packages that no other package requires.
        :returns: the normalized names of the packages.
        :raises PipxError: when uv cannot list the packages.
        """
        if not_required:
            from pipx.venv_inspect import list_not_required_packages  # ruff:ignore[import-outside-top-level]  # pulls in packaging.requirements, slows startup

            return list_not_required_packages(venv_python)

        cmd: Final = [*self._uv_pip_command("list", venv_python, verbose=False), "--format", "json"]
        process: Final = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=self._env_overrides())
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
        """Return the installed packages that have a newer version in the index.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param index_args: the index arguments to query.
        :param exclude: the names of the packages to leave out of the check.
        :returns: the outdated packages.
        """
        reject_empty_index(index_args)
        cmd: Final = [
            *self._uv_pip_command("list", venv_python, verbose=False),
            "--outdated",
            "--format=json",
            *self._default_index_args(index_args),
            *(f"--exclude={name}" for name in exclude),
        ]
        process: Final = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=self._env_overrides())
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
        """Run a pip command through ``uv pip`` in an environment.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param args: the pip subcommand and its arguments.
        :param capture_stdout: capture the standard output instead of showing it.
        :param capture_stderr: capture the standard error instead of showing it.
        :param verbose: show the output of uv.
        :param in_working_dir: run in the current working directory instead of the environment's root.
        :returns: the completed uv process.
        """
        # with no args, show pip's help as `pipx runpip TOOL` does under the pip backend
        cmd: list[str | Path] = [self._binary, "pip", args[0] if args else "--help", "--python", str(venv_python)]
        # As with pip, verbose only means "do not silence": uv's --verbose prints DEBUG logs, and runpip always sets it
        if verbose:
            cmd += args[1:]
        else:
            if args:
                cmd.append("--quiet")
            cmd += self._strip_pip_quiet_flags(args[1:])
        return run_subprocess(
            cmd,
            run_dir=None if in_working_dir else str(venv_root),
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            env_overrides=self._env_overrides(),
            # uncaptured, it talks to the user's terminal, as under `pipx runpip`
            interactive=not (capture_stdout or capture_stderr),
        )


def resolve_uv_binary() -> Path:
    """Return the path of the uv executable.

    :returns: the path of the executable.
    :raises PipxError: when no uv executable can be found.
    """
    # checks the version here so callers outside UvBackend, such as `pipx run`'s uv tool run shortcut, get pipx's
    # version error instead of an opaque one from uv
    binary, _ = find_uv_binary()
    if binary is None:
        msg = (
            "The uv backend was requested but the 'uv' executable could not be found.\n"
            "Install pipx with the uv extra (`pipx install pipx[uv]`) or place 'uv' on your PATH.\n"
            "Alternatively, run with `--backend pip` (or set PIPX_DEFAULT_BACKEND=pip)."
        )
        raise PipxError(msg)
    _check_uv_version(binary)
    return binary


# cached so `upgrade-all` and similar loops over many venvs walk PATH once
@cache
def find_uv_binary() -> tuple[Path | None, str]:
    """Find the uv executable, preferring the one bundled with the uv package over the one on the PATH.

    :returns: the path of the executable, or None when none is found, and where it came from: ``bundled``, ``path`` or
        ``missing``.
    """
    if _FIND_UV_BIN_FROM_EXTRA is not None:
        try:
            bundled: Final = Path(_FIND_UV_BIN_FROM_EXTRA())
        except FileNotFoundError:
            pass
        else:
            # is_file rejects a stale path from a half-installed extra; _binary_runs catches a binary that fails to
            # start (missing dylib, ENOEXEC), so the search falls through to PATH instead of erroring later
            if bundled.is_file() and _binary_runs(bundled):
                return bundled, "bundled"
    # probe the PATH candidate too, so a broken or hanging uv on PATH is skipped here instead of stalling the later
    # version check
    if (path := shutil.which("uv")) and _binary_runs(candidate := Path(path)):
        return candidate, "path"
    return None, "missing"


def _binary_runs(binary: Path) -> bool:
    try:
        process: Final = _run_uv_version(binary)
    except (OSError, subprocess.TimeoutExpired) as exc:
        _LOGGER.debug("uv launch probe failed for %s: %s", binary, exc)
        return False
    if process.returncode != 0 or not _VERSION_RE.search(process.stdout):
        _LOGGER.debug(
            "uv launch probe rejected %s: rc=%s, stdout=%r, stderr=%r",
            binary,
            process.returncode,
            process.stdout,
            process.stderr,
        )
        return False
    return True


# cached so the launch probe, the version floor check and `upgrade-all` over many venvs share one run of uv
@cache
def _run_uv_version(binary: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(binary), "--version"], check=False, text=True, capture_output=True, timeout=10)


def _check_uv_version(binary: Path) -> Version:
    if (version := _uv_version(binary)) < _MIN_UV_VERSION:
        msg = (
            f"pipx needs uv>={_MIN_UV_VERSION}, but {binary} reports {version}.\n"
            "Upgrade uv (`uv self update` or reinstall pipx[uv]), or run with `--backend pip` to bypass."
        )
        raise PipxError(msg)
    return version


def _uv_version(binary: Path) -> Version:
    try:
        process: Final = _run_uv_version(binary)
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = (
            f"Could not run {binary} --version ({exc}).\n"
            "Repair or reinstall uv, or run with `--backend pip` (or set PIPX_DEFAULT_BACKEND=pip)."
        )
        raise PipxError(msg) from exc
    if (match := _VERSION_RE.search(process.stdout)) is None:
        msg = (
            f"Could not parse uv version from {binary} "
            f"(rc={process.returncode}, stdout={process.stdout!r}, stderr={process.stderr!r})."
        )
        raise PipxError(msg)
    try:
        return Version(match.group(1))
    except InvalidVersion as exc:
        msg = f"Unrecognized uv version {match.group(1)!r}."
        raise PipxError(msg) from exc


# cached so auto-detection, which runs once per venv, warns once per process
@cache
def uv_meets_minimum_version(binary: Path) -> bool:
    """Return whether a uv binary is new enough for pipx to use it, and log a warning when it is not.

    :param binary: the path of the uv executable.
    :returns: whether the binary meets the minimum version.
    """
    if (version := _uv_version(binary)) >= _MIN_UV_VERSION:
        return True
    _LOGGER.warning(
        "Skipping uv %s at %s since pipx needs uv>=%s; using pip. "
        "Upgrade uv, or set PIPX_DEFAULT_BACKEND=pip to silence this.",
        version,
        binary,
        _MIN_UV_VERSION,
    )
    return False


__all__ = [
    "PIP_TO_UV_INDEX_FLAGS",
    "UvBackend",
    "find_uv_binary",
    "resolve_uv_binary",
    "uv_meets_minimum_version",
]
