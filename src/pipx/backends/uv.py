from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.version import InvalidVersion, Version

from pipx.animate import animate
from pipx.backends._base import UV, Backend
from pipx.util import (
    PipxError,
    run_subprocess,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


# Imported into a temporary, then assigned through Final and deleted so mypy
# sees one Final binding (it rejects redefinition across try/except branches).
try:
    from uv import find_uv_bin as _uv_bin_from_extra  # type: ignore[import-not-found]
except ImportError:
    _uv_bin_from_extra = None
_FIND_UV_BIN_FROM_EXTRA: Final[Callable[[], str] | None] = _uv_bin_from_extra
del _uv_bin_from_extra
_MIN_UV_VERSION: Final[Version] = Version("0.4.0")
_VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    uv \s+        # the literal "uv " prefix from `uv --version`
    (\S+)         # capture the version token; PEP 440 parser validates it
    """,
    re.VERBOSE,
)
# Stripping VIRTUAL_ENV stops uv from auto-targeting an active venv when no
# ``--python`` flag is passed.
_UV_ENV_OVERRIDES: Final[dict[str, str | None]] = {"VIRTUAL_ENV": None, "UV_NO_PROGRESS": "1"}


class UvBackend(Backend):
    name = UV

    def __init__(self) -> None:
        self._binary = resolve_uv_binary()
        _, self._source = find_uv_binary()
        version = _check_uv_version(self._binary)
        _LOGGER.info(f"using {self._source} uv {version} from {self._binary}")

    def needs_shared_libs(self) -> bool:
        return False

    def upgrade_packaging_libraries(self, venv_python: Path, pip_args: list[str], *, verbose: bool) -> None:
        del venv_python, pip_args, verbose  # uv venvs ship no pip to upgrade.

    def create_venv(
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
            raise PipxError(
                "The uv backend cannot create a virtual environment with pip preinstalled.\n"
                "Reinstall the package with `--backend pip` (or unset PIPX_DEFAULT_BACKEND)."
            )
        cmd: list[str | Path] = [self._binary, "venv", "--python", python, *venv_args]
        cmd.append("--verbose" if verbose else "--quiet")
        cmd.append(str(root))
        with animate("creating virtual environment", not verbose):
            process = run_subprocess(cmd, run_dir=str(root), env_overrides=_UV_ENV_OVERRIDES)
        subprocess_post_check(process)

    def install(
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
    ) -> CompletedProcess[str]:
        cmd = self._uv_pip_command("install", venv_python, verbose=verbose)
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
            env_overrides=_UV_ENV_OVERRIDES,
        )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process, tool_name="uv")
        else:
            subprocess_post_check(process, raise_error=False)
        return process

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
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_UV_ENV_OVERRIDES)
        subprocess_post_check(process)
        return process

    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool = False,
    ) -> set[str]:
        cmd = self._uv_pip_command("list", venv_python, verbose=False)
        cmd += ["--format", "json"]
        if not_required:
            cmd.append("--not-required")
        process = run_subprocess(cmd, run_dir=str(venv_root), env_overrides=_UV_ENV_OVERRIDES)
        if process.returncode != 0:
            raise PipxError(
                f"Failed to execute {process.args}.\n"
                f"Process exited with return code {process.returncode}.\n"
                f"stderr: {process.stderr}"
            )
        return {entry["name"] for entry in json.loads(process.stdout.strip())}

    def run_raw_pip(
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
            env_overrides=_UV_ENV_OVERRIDES,
        )

    def _uv_pip_command(self, subcommand: str, venv_python: Path, *, verbose: bool) -> list[str | Path]:
        cmd: list[str | Path] = [self._binary, "pip", subcommand, "--python", str(venv_python)]
        cmd.append("--verbose" if verbose else "--quiet")
        return cmd


def resolve_uv_binary() -> Path:
    # The version check fires here so non-Backend callers (e.g. ``pipx run``'s
    # uv-tool-run shortcut) still get the "needs uv >= X" message rather than
    # an opaque uv-side error.
    binary, _ = find_uv_binary()
    if binary is None:
        raise PipxError(
            "The uv backend was requested but the 'uv' executable could not be found.\n"
            "Install pipx with the uv extra (`pipx install pipx[uv]`) or place 'uv' on your PATH.\n"
            "Alternatively, run with `--backend pip` (or set PIPX_DEFAULT_BACKEND=pip)."
        )
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
    if path := shutil.which("uv"):
        return Path(path), "path"
    return None, "missing"


def _binary_runs(binary: Path) -> bool:
    # Liveness probe; full floor-version check stays in ``_check_uv_version``.
    try:
        process = subprocess.run([str(binary), "--version"], check=False, text=True, capture_output=True, timeout=10)
    except OSError as exc:
        _LOGGER.debug(f"uv launch probe failed for {binary}: {exc}")
        return False
    if process.returncode != 0 or not _VERSION_RE.search(process.stdout):
        _LOGGER.debug(
            f"uv launch probe rejected {binary}: "
            f"rc={process.returncode}, stdout={process.stdout!r}, stderr={process.stderr!r}"
        )
        return False
    return True


@cache
def _check_uv_version(binary: Path) -> Version:
    # Cached so ``upgrade-all`` over many venvs doesn't fork uv repeatedly.
    process = subprocess.run([str(binary), "--version"], check=False, text=True, capture_output=True)
    if (match := _VERSION_RE.search(process.stdout)) is None:
        raise PipxError(
            f"Could not parse uv version from {binary} "
            f"(rc={process.returncode}, stdout={process.stdout!r}, stderr={process.stderr!r})."
        )
    try:
        version = Version(match.group(1))
    except InvalidVersion as exc:
        raise PipxError(f"Unrecognized uv version {match.group(1)!r}.") from exc
    if version < _MIN_UV_VERSION:
        raise PipxError(
            f"pipx needs uv>={_MIN_UV_VERSION}, but {binary} reports {version}.\n"
            "Upgrade uv (`uv self update` or reinstall pipx[uv]), or run with `--backend pip` to bypass."
        )
    return version


def _strip_pip_quiet_flags(pip_args: list[str]) -> list[str]:
    return [arg for arg in pip_args if arg not in ("-q", "-qq", "--quiet")]


__all__ = [
    "UvBackend",
    "find_uv_binary",
    "resolve_uv_binary",
]
