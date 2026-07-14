from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Final

from pipx.animate import animate
from pipx.backends._base import PIP, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.constants import PIPX_SHARED_PTH
from pipx.shared_libs import shared_libs
from pipx.util import (
    PipxError,
    get_site_packages,
    get_venv_paths,
    run_subprocess,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)
from pipx.venv_inspect import list_not_required_packages

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class PipBackend(Backend):
    name = PIP

    def needs_shared_libs(self) -> bool:
        return True

    def upgrade_packaging_libraries(
        self,
        venv_python: Path,
        pip_args: list[str],
        *,
        verbose: bool,
    ) -> None:
        # Reached only for ``pipx install pip``-style venvs that ship pip
        # in-tree; shared-libs venvs upgrade through ``shared_libs.upgrade``.
        process = run_subprocess(
            [str(venv_python), "-m", "pip", "--no-input", "install", "--upgrade", *pip_args, "pip"],
            run_dir=str(venv_python.parent.parent),
        )
        subprocess_post_check(process)

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
        cmd = [python, "-m", "venv"]
        if not include_pip:
            cmd.append("--without-pip")
        cmd += [*venv_args, str(root)]
        with animate("creating virtual environment", not verbose):
            venv_process = run_subprocess(cmd, run_dir=str(root))
        subprocess_post_check(venv_process)

        shared_libs.create(verbose=verbose, pip_args=pip_args)
        if not include_pip:
            _, python_path, _ = get_venv_paths(root)
            pipx_pth = get_site_packages(python_path) / PIPX_SHARED_PTH
            pipx_pth.write_text(f"{shared_libs.site_packages}\n")

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
        cmd: list[str] = [str(venv_python), "-m", "pip", "--no-input", "install"]
        if upgrade:
            cmd.append("--upgrade")
        if no_deps:
            cmd.append("--no-dependencies")
        if verbose:
            cmd.append("--progress-bar=on")
        cmd += [*pip_args, *requirements]
        process = run_subprocess(
            cmd,
            log_stdout=not log_pip_errors,
            log_stderr=not log_pip_errors,
            run_dir=str(venv_root),
            stream_output=verbose,
        )
        if log_pip_errors:
            subprocess_post_check_handle_pip_error(process)
        return process

    @staticmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        return [] if not cooldown_days else ["--uploaded-prior-to", f"P{cooldown_days}D"]

    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        package: str,
        verbose: bool,
    ) -> CompletedProcess[str]:
        cmd = [str(venv_python), "-m", "pip", "uninstall", "-y", package]
        if not verbose:
            cmd.append("-q")
        process = run_subprocess(cmd, run_dir=str(venv_root))
        subprocess_post_check(process)
        return process

    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool = False,
    ) -> set[str]:
        del venv_root
        if not_required:
            return list_not_required_packages(venv_python)
        cmd = [str(venv_python), "-m", "pip", "list", "--format=json"]
        process = run_subprocess(cmd)
        if process.returncode != 0:
            raise PipxError(
                f"Failed to execute {process.args}.\n"
                f"Process exited with return code {process.returncode}.\n"
                f"stderr: {process.stderr}"
            )
        return {entry["name"] for entry in json.loads(process.stdout.strip())}

    def list_outdated(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        index_args: list[str],
    ) -> tuple[OutdatedPackage, ...]:
        process = run_subprocess(
            [str(venv_python), "-m", "pip", "list", "--outdated", "--format=json", *index_args],
            run_dir=str(venv_root),
        )
        return outdated_packages_from_process(process)

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
        cmd = [str(venv_python), "-m", "pip", *args]
        if not verbose:
            cmd.append("-q")
        return run_subprocess(
            cmd,
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            run_dir=str(venv_root),
        )


__all__ = [
    "PipBackend",
]
