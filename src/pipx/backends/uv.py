from __future__ import annotations

__lazy_modules__ = ["importlib", "json", "pathlib", "pipx", "pipx.util", "shutil", "subprocess"]

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

from pipx import paths
from pipx.animate import animate
from pipx.backends._base import UV, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.util import (
    PipxError,
    reject_empty_index,
    run_subprocess,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
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

    def needs_shared_libs(self) -> bool:  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        return False

    def upgrade_packaging_libraries(  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        self, venv_python: Path, pip_args: list[str], *, verbose: bool
    ) -> None:
        del venv_python, pip_args, verbose  # uv venvs ship no pip to upgrade.

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
        verbose: bool = False,
    ) -> CompletedProcess[str]:
        reject_empty_index(pip_args)
        cmd = self._uv_pip_command("install", venv_python, verbose=verbose)
        # uv's --upgrade re-resolves every dependency, pip's only-if-needed default upgrades only the named package
        if upgrade_package is not None:
            cmd += ["--upgrade-package", upgrade_package]
        if no_deps:
            cmd.append("--no-deps")
        cmd += [*_default_index_args(_strip_pip_quiet_flags(pip_args)), *requirements]
        process = run_subprocess(
            cmd,
            run_dir=str(venv_root),
            log_stdout=not log_pip_errors,
            log_stderr=not log_pip_errors,
            env_overrides=_uv_env_overrides(),
            stream_output=verbose,
        )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process, tool_name="uv", streamed=verbose)
        return process

    @staticmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        return [] if not cooldown_days else ["--exclude-newer", f"P{cooldown_days}D"]

    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        packages: Sequence[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        cmd = self._uv_pip_command("uninstall", venv_python, verbose=verbose)
        cmd.extend(packages)
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
            from pipx.venv_inspect import list_not_required_packages  # ruff:ignore[import-outside-top-level]  # pulls in packaging.requirements, slows startup

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
        exclude: list[str],
    ) -> tuple[OutdatedPackage, ...]:
        reject_empty_index(index_args)
        cmd = self._uv_pip_command("list", venv_python, verbose=False)
        cmd += [
            "--outdated",
            "--format=json",
            *_default_index_args(index_args),
            *(f"--exclude={name}" for name in exclude),
        ]
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_uv_env_overrides())
        return outdated_packages_from_process(process)

    def run_raw_pip(  # ruff:ignore[too-many-arguments]  # Backend interface method passing raw pip controls through
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        args: list[str],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        verbose: bool = False,
        in_working_dir: bool = False,
    ) -> CompletedProcess[str]:
        # Mirror pip-backend ``pipx runpip TOOL`` (no args -> pip's help).
        cmd: list[str | Path] = [self._binary, "pip", args[0] if args else "--help"]
        cmd += ["--python", str(venv_python)]
        # As with pip, verbose only means "do not silence": uv's --verbose prints DEBUG logs, and runpip always sets it
        if verbose:
            cmd += args[1:]
        else:
            if args:
                cmd.append("--quiet")
            cmd += _strip_pip_quiet_flags(args[1:])
        return run_subprocess(
            cmd,
            run_dir=None if in_working_dir else str(venv_root),
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            env_overrides=_uv_env_overrides(),
            # uncaptured, it talks to the user's terminal, as under `pipx runpip`
            interactive=not (capture_stdout or capture_stderr),
        )

    def _uv_pip_command(
        self,
        subcommand: str,
        venv_python: Path,
        *,
        verbose: bool,
    ) -> list[str | Path]:
        cmd: list[str | Path] = [self._binary, "pip", subcommand, "--python", str(venv_python)]
        cmd.append("--verbose" if verbose else "--quiet")
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
        process = _run_uv_version(binary)
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
def uv_meets_minimum_version(binary: Path) -> bool:
    # Cached so auto-detection, which runs once per venv, warns once per process.
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
        process = _run_uv_version(binary)
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


@cache
def _run_uv_version(binary: Path) -> subprocess.CompletedProcess[str]:
    # Cached so the liveness probe, the version floor check and ``upgrade-all`` over many venvs share one fork of uv.
    return subprocess.run(
        [str(binary), "--version"], check=False, text=True, capture_output=True, timeout=_UV_PROBE_TIMEOUT
    )


def _uv_env_overrides() -> dict[str, str | None]:
    # Stripping VIRTUAL_ENV stops uv from auto-targeting an active venv when no ``--python`` flag is passed. pipx shows
    # its own spinner in place of uv's bar, and uv hides the bar under --verbose anyway. UV_PROJECT moves uv's
    # project-config search from its working directory, which can sit in a shared /tmp, to pipx's home; user and system
    # config still load.
    return {"VIRTUAL_ENV": None, "UV_NO_PROGRESS": "1", "UV_PROJECT": str(paths.ctx.home)}


def _strip_pip_quiet_flags(pip_args: list[str]) -> list[str]:
    return [arg for arg in pip_args if arg not in {"-q", "-qq", "--quiet"}]


def _default_index_args(pip_args: list[str]) -> list[str]:
    # uv lets UV_DEFAULT_INDEX override a command-line --index-url, but not --default-index
    return [
        f"--default-index{separator}{value}"
        if flag in {"--index-url", "-i"}
        else f"--default-index={arg[2:]}"
        if arg.startswith("-i")
        else arg
        for arg in pip_args
        for flag, separator, value in [arg.partition("=")]
    ]


__all__ = [
    "UvBackend",
    "find_uv_binary",
    "resolve_uv_binary",
    "uv_meets_minimum_version",
]
