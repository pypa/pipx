from __future__ import annotations

__lazy_modules__ = [
    "packaging.utils",
    "pathlib",
    "pipx.commands.common",
    "pipx.commands.transaction",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.util",
    "pipx.venv",
]

from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.commands.common import package_name_from_spec
from pipx.commands.transaction import preserve_venv, runs_from_venv
from pipx.options import BackendOptions, ExposureOptions
from pipx.package_specifier import absolute_path_pip_args, extract_index_options, install_specs, replace_index_options
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from pipx.constants import ExitCode


def run_pip(package: str, venv_dir: Path, pip_args: list[str], *, verbose: bool) -> ExitCode:
    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        msg = f"pipx has no venv for {package!r}; run 'pipx list' to see the installed packages"
        raise PipxError(msg)
    venv.verbose = True
    # pip may change the pipx running this, which keeps importing its own version from the copy
    with preserve_venv(venv_dir, enabled=runs_from_venv(venv_dir)):
        exit_code: Final[ExitCode] = venv.run_pip_get_exit_code(pip_args)
    if exit_code == 0:
        _sync_main_package_metadata_after_runpip_install(venv, pip_args)
    return exit_code


def _sync_main_package_metadata_after_runpip_install(venv: Venv, pip_args: list[str]) -> None:
    main_package: Final = venv.pipx_metadata.main_package
    if main_package.package is None:
        return

    for package_spec, editable in install_specs(pip_args[1:]) if pip_args[:1] == ["install"] else []:
        package_name = package_name_from_spec(
            package_spec,
            str(venv.python_path),
            pip_args=["--editable"] if editable else [],
            verbose=venv.verbose,
            backend=BackendOptions(cli=venv.backend_name),
        )
        if canonicalize_name(package_name) != canonicalize_name(main_package.package):
            continue

        venv.update_package_metadata(
            package_name=main_package.package,
            package_or_url=package_spec,
            pip_args=_updated_main_package_pip_args(main_package.pip_args, pip_args, editable=editable),
            exposure=ExposureOptions.recorded(main_package),
            is_main_package=True,
            pinned=main_package.pinned,
        )
        return


def _updated_main_package_pip_args(
    existing_pip_args: list[str], runpip_args: list[str], *, editable: bool
) -> list[str]:
    pip_args = [arg for arg in existing_pip_args if arg not in {"-e", "--editable"}]
    # pip resolved the new spec on the indexes this command named, so upgrade and reinstall must ask the same ones; it
    # read relative paths from the caller's directory, while pipx reads a recorded relative path against the venv
    if index_args := extract_index_options(runpip_args):
        pip_args = replace_index_options(pip_args, absolute_path_pip_args(index_args, Path.cwd()))
    if editable:
        pip_args.append("--editable")
    return pip_args


__all__ = [
    "run_pip",
]
