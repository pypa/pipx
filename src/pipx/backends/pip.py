from __future__ import annotations

__lazy_modules__ = ["json", "packaging.version", "pipx.shared_libs", "pipx.util"]

import json
import logging
from typing import TYPE_CHECKING, Final

from packaging.version import InvalidVersion, Version

from pipx.animate import animate
from pipx.backends._base import PIP, Backend, OutdatedPackage, outdated_packages_from_process
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.shared_libs import shared_libs
from pipx.util import (
    PipxError,
    get_site_packages,
    get_venv_paths,
    run_subprocess,
    safe_unlink,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from subprocess import CompletedProcess

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class PipBackend(Backend):
    name = PIP

    def needs_shared_libs(self) -> bool:  # ruff:ignore[no-self-use]  # Backend interface method, must dispatch polymorphically
        return True

    def upgrade_packaging_libraries(
        self,
        venv_python: Path,
        pip_args: list[str],
        *,
        verbose: bool,
    ) -> None:
        del verbose  # pip's upgrade output is not gated on verbosity here
        # Reached only for ``pipx install pip``-style venvs that ship pip
        # in-tree; shared-libs venvs upgrade through ``shared_libs.upgrade``.
        self._drop_site_config(venv_python.parent.parent)
        process = run_subprocess(
            [str(venv_python), "-m", "pip", "--no-input", "install", "--upgrade", *pip_args, "pip"],
            run_dir=str(venv_python.parent.parent),
        )
        subprocess_post_check(process)

    @staticmethod
    def _drop_site_config(venv_root: Path) -> None:
        # pip reads <sys.prefix>/pip.conf over the user's own configuration, and any installed wheel can unpack a data
        # file there; pip has no switch that skips only this file (--isolated still reads it, PIP_CONFIG_FILE=os.devnull
        # drops every file), so a ``target`` in it would make the next upgrade install outside the venv
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
        cmd = [python, "-m", "venv"]
        if not include_pip:
            cmd.append("--without-pip")
        cmd += [*venv_args, str(root)]
        with animate("creating virtual environment", do_animation=not verbose):
            venv_process = run_subprocess(cmd, run_dir=str(root))
        subprocess_post_check(venv_process)

        shared_libs.create(verbose=verbose, pip_args=pip_args)
        if not include_pip:
            _, python_path, _ = get_venv_paths(root)
            purelib = get_site_packages(python_path)[0]
            purelib.mkdir(parents=True, exist_ok=True)
            (purelib / PIPX_SHARED_PTH).write_text("".join(f"{path}\n" for path in shared_libs.site_packages))

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
        verbose: bool = False,
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
        process = shared_libs.run_repairing_pip(
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
        verbose: bool = False,
    ) -> CompletedProcess[str]:
        process = shared_libs.run_repairing_pip(
            lambda: run_subprocess([str(venv_python), "-m", "pip", "--version"], run_dir=str(venv_root)),
            pip_args=pip_args,
            verbose=verbose,
        )
        try:
            version: Version | None = Version(process.stdout.split()[1])
        except (IndexError, InvalidVersion):
            version = None
        # older pip reads ``--requirement pylock.toml`` as a requirements file, applying its lines as options
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
        cmd = [str(venv_python), "-m", "pip", "uninstall", "-y", *packages]
        if not verbose:
            cmd.append("-q")
        self._drop_site_config(venv_root)
        process = shared_libs.run_repairing_pip(
            lambda: run_subprocess(cmd, run_dir=str(venv_root)), pip_args=[], verbose=verbose
        )
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
        cmd = [str(venv_python), "-m", "pip", "list", "--format=json"]
        self._drop_site_config(venv_root)
        process = shared_libs.run_repairing_pip(lambda: run_subprocess(cmd), pip_args=[], verbose=False)
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
        process = shared_libs.run_repairing_pip(
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
        verbose: bool = False,
        in_working_dir: bool = False,
    ) -> CompletedProcess[str]:
        cmd = [str(venv_python), "-m", "pip", *args]
        if not verbose:
            cmd.append("-q")
        self._drop_site_config(venv_root)
        return shared_libs.run_repairing_pip(
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


__all__ = [
    "PipBackend",
]
