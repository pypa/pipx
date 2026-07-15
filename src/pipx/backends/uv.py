from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from packaging.version import InvalidVersion, Version

from pipx.animate import animate
from pipx.backends._base import UV, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.util import (
    PipxError,
    run_subprocess,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)
from pipx.venv_inspect import list_not_required_packages

if TYPE_CHECKING:
    from collections.abc import Callable
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _load_uv_bin_finder() -> Callable[[], str] | None:
    try:
        return cast("Callable[[], str]", import_module("uv").find_uv_bin)
    except (AttributeError, ImportError):
        return None


_FIND_UV_BIN_FROM_EXTRA: Final[Callable[[], str] | None] = _load_uv_bin_finder()
_MIN_UV_VERSION: Final[Version] = Version("0.9.17")
_VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    uv \s+        # the literal "uv " prefix from `uv --version`
    (\S+)         # capture the version token; PEP 440 parser validates it
    """,
    re.VERBOSE,
)
_UV_PROBE_TIMEOUT: Final[int] = 10


class UvBackend(Backend):
    name = UV

    def __init__(self) -> None:
        self._binary = resolve_uv_binary()
        _, self._source = find_uv_binary()
        version = _check_uv_version(self._binary)
        _LOGGER.info("using %s uv %s from %s", self._source, version, self._binary)

    def needs_shared_libs(self) -> bool:  # noqa: PLR6301  # Backend interface method, must dispatch polymorphically
        return False

    def upgrade_packaging_libraries(  # noqa: PLR6301  # Backend interface method, must dispatch polymorphically
        self, venv_python: Path, pip_args: list[str], *, verbose: bool
    ) -> None:
        del venv_python, pip_args, verbose  # uv venvs ship no pip to upgrade.

    def create_venv(  # noqa: PLR0913  # Backend interface method mirroring venv-creation inputs
        self,
        root: Path,
        *,
        python: str,
        venv_args: list[str],
        pip_args: list[str],
        include_pip: bool,
        verbose: bool,
    ) -> None:
        del pip_args  # uv venv has no pip to seed.
        if include_pip:
            msg = (
                "The uv backend cannot create a virtual environment with pip preinstalled.\n"
                "Reinstall the package with `--backend pip` (or unset PIPX_DEFAULT_BACKEND)."
            )
            raise PipxError(msg)
        cmd: list[str | Path] = [self._binary, "venv", "--python", python, "--allow-existing", *venv_args]
        cmd.extend(("--verbose" if verbose else "--quiet", str(root)))
        with animate("creating virtual environment", do_animation=not verbose):
            process = run_subprocess(cmd, run_dir=str(root), env_overrides=_uv_env_overrides())
        subprocess_post_check(process)

    def install(  # noqa: PLR0913  # Backend interface method mapping flags to uv options
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        requirements: list[str],
        pip_args: list[str],
        no_deps: bool = False,
        upgrade: bool = False,
        log_pip_errors: bool = True,
        verbose: bool = False,
        progress: bool = False,
    ) -> CompletedProcess[str]:
        cmd = self._uv_pip_command("install", venv_python, verbose=verbose, progress=progress)
        if upgrade:
            cmd.append("--upgrade")
        if no_deps:
            cmd.append("--no-deps")
        cmd += [*_strip_pip_quiet_flags(pip_args), *requirements]
        process = run_subprocess(
            cmd,
            run_dir=str(venv_root),
            log_stdout=not log_pip_errors,
            log_stderr=not log_pip_errors,
            env_overrides=_uv_env_overrides(progress=progress),
            stream_output=verbose or progress,
        )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process, tool_name="uv")
        return process

    @staticmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        return [] if not cooldown_days else ["--exclude-newer", f"P{cooldown_days}D"]

    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        package: str,
        verbose: bool,
    ) -> CompletedProcess[str]:
        cmd = self._uv_pip_command("uninstall", venv_python, verbose=verbose)
        cmd.append(package)
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_uv_env_overrides())
        subprocess_post_check(process)
        return process

    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool = False,
    ) -> set[str]:
        if not_required:
            return list_not_required_packages(venv_python)

        cmd = self._uv_pip_command("list", venv_python, verbose=False)
        cmd += ["--format", "json"]
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_uv_env_overrides())
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
    ) -> tuple[OutdatedPackage, ...]:
        cmd = self._uv_pip_command("list", venv_python, verbose=False)
        cmd += ["--outdated", "--format=json", *index_args]
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_uv_env_overrides())
        return outdated_packages_from_process(process)

    def run_raw_pip(  # noqa: PLR0913  # Backend interface method passing raw pip controls through
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        args: list[str],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        verbose: bool = False,
    ) -> CompletedProcess[str]:
        # Mirror pip-backend ``pipx runpip TOOL`` (no args -> pip's help).
        cmd: list[str | Path] = [self._binary, "pip", args[0] if args else "--help"]
        cmd += ["--python", str(venv_python)]
        if verbose:
            cmd.append("--verbose")
        elif args:
            cmd.append("--quiet")
        cmd += _strip_pip_quiet_flags(args[1:])
        return run_subprocess(
            cmd,
            run_dir=str(venv_root),
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            env_overrides=_uv_env_overrides(),
        )

    def _uv_pip_command(
        self,
        subcommand: str,
        venv_python: Path,
        *,
        verbose: bool,
        progress: bool = False,
    ) -> list[str | Path]:
        cmd: list[str | Path] = [self._binary, "pip", subcommand, "--python", str(venv_python)]
        # uv hides its progress bar under both --verbose and --quiet, so drawing one means passing neither
        if verbose:
            cmd.append("--verbose")
        elif not progress:
            cmd.append("--quiet")
        return cmd


def resolve_uv_binary() -> Path:
    # The version check fires here so non-Backend callers (e.g. ``pipx run``'s
    # uv-tool-run shortcut) still get the "needs uv >= X" message rather than
    # an opaque uv-side error.
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


@cache
def find_uv_binary() -> tuple[Path | None, str]:
    # Cached so ``upgrade-all`` and similar hot loops don't re-walk PATH per venv.
    if _FIND_UV_BIN_FROM_EXTRA is not None:
        try:
            bundled = Path(_FIND_UV_BIN_FROM_EXTRA())
        except FileNotFoundError:
            pass
        else:
            # ``is_file`` rejects a stale path from a half-installed extra;
            # ``_binary_runs`` catches the exec-fails case (missing dylib,
            # ENOEXEC) so we fall through to PATH instead of erroring later.
            if bundled.is_file() and _binary_runs(bundled):
                return bundled, "bundled"
    # Probe the PATH candidate too, so a broken or hanging ``uv`` on PATH is
    # skipped here instead of stalling the later version check.
    if (path := shutil.which("uv")) and _binary_runs(candidate := Path(path)):
        return candidate, "path"
    return None, "missing"


def _binary_runs(binary: Path) -> bool:
    # Liveness probe; full floor-version check stays in ``_check_uv_version``.
    try:
        process = subprocess.run(
            [str(binary), "--version"], check=False, text=True, capture_output=True, timeout=_UV_PROBE_TIMEOUT
        )
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


@cache
def _check_uv_version(binary: Path) -> Version:
    # Cached so ``upgrade-all`` over many venvs doesn't fork uv repeatedly.
    try:
        process = subprocess.run(
            [str(binary), "--version"], check=False, text=True, capture_output=True, timeout=_UV_PROBE_TIMEOUT
        )
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
        version = Version(match.group(1))
    except InvalidVersion as exc:
        msg = f"Unrecognized uv version {match.group(1)!r}."
        raise PipxError(msg) from exc
    if version < _MIN_UV_VERSION:
        msg = (
            f"pipx needs uv>={_MIN_UV_VERSION}, but {binary} reports {version}.\n"
            "Upgrade uv (`uv self update` or reinstall pipx[uv]), or run with `--backend pip` to bypass."
        )
        raise PipxError(msg)
    return version


def _uv_env_overrides(*, progress: bool = False) -> dict[str, str | None]:
    # Stripping VIRTUAL_ENV stops uv from auto-targeting an active venv when no ``--python`` flag is passed.
    overrides: dict[str, str | None] = {"VIRTUAL_ENV": None}
    # pipx draws its own spinner in quiet, JSON, and non-interactive runs, so silence uv's bar there; when pipx does
    # want the bar (progress=True) leave the caller's UV_NO_PROGRESS untouched so their preference wins.
    if not progress:
        overrides["UV_NO_PROGRESS"] = "1"
    return overrides


def _strip_pip_quiet_flags(pip_args: list[str]) -> list[str]:
    return [arg for arg in pip_args if arg not in {"-q", "-qq", "--quiet"}]


__all__ = [
    "UvBackend",
    "find_uv_binary",
    "resolve_uv_binary",
]
