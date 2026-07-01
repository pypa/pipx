from pathlib import Path

from packaging.utils import canonicalize_name

from pipx.commands.common import package_name_from_spec
from pipx.constants import ExitCode
from pipx.util import PipxError
from pipx.venv import Venv


def _iter_install_specs(pip_args: list[str]) -> list[tuple[str, bool]]:
    if not pip_args or pip_args[0] != "install":
        return []

    specs: list[tuple[str, bool]] = []
    options_with_value = {
        "-c",
        "--constraint",
        "--config-settings",
        "-f",
        "--find-links",
        "-i",
        "--index-url",
        "--extra-index-url",
        "--implementation",
        "--platform",
        "--prefix",
        "--python-version",
        "-r",
        "--requirement",
        "--report",
        "--root",
        "--src",
        "--target",
        "--trusted-host",
    }
    options_with_value_prefixes = (
        "--constraint=",
        "--config-settings=",
        "--find-links=",
        "--index-url=",
        "--extra-index-url=",
        "--implementation=",
        "--platform=",
        "--prefix=",
        "--python-version=",
        "--requirement=",
        "--report=",
        "--root=",
        "--src=",
        "--target=",
        "--trusted-host=",
    )

    index = 1
    while index < len(pip_args):
        arg = pip_args[index]
        if arg in {"-e", "--editable"}:
            if index + 1 < len(pip_args):
                specs.append((pip_args[index + 1], True))
            index += 2
            continue
        if arg.startswith("--editable="):
            specs.append((arg.split("=", 1)[1], True))
            index += 1
            continue
        if arg in options_with_value:
            index += 2
            continue
        if arg.startswith(options_with_value_prefixes) or arg.startswith("-"):
            index += 1
            continue
        specs.append((arg, False))
        index += 1

    return specs


def _updated_main_package_pip_args(existing_pip_args: list[str], editable: bool) -> list[str]:
    pip_args = [arg for arg in existing_pip_args if arg not in {"-e", "--editable"}]
    if editable:
        pip_args.append("--editable")
    return pip_args


def _sync_main_package_metadata_after_runpip_install(venv: Venv, pip_args: list[str]) -> None:
    main_package = venv.pipx_metadata.main_package
    if main_package.package is None:
        return

    for package_spec, editable in _iter_install_specs(pip_args):
        package_name = package_name_from_spec(
            package_spec,
            str(venv.python_path),
            pip_args=["--editable"] if editable else [],
            verbose=venv.verbose,
            backend=venv.backend_name,
        )
        if canonicalize_name(package_name) != canonicalize_name(main_package.package):
            continue

        venv.update_package_metadata(
            package_name=main_package.package,
            package_or_url=package_spec,
            pip_args=_updated_main_package_pip_args(main_package.pip_args, editable),
            include_dependencies=main_package.include_dependencies,
            include_apps=main_package.include_apps,
            is_main_package=True,
            suffix=main_package.suffix,
            pinned=main_package.pinned,
        )
        return


def run_pip(package: str, venv_dir: Path, pip_args: list[str], verbose: bool) -> ExitCode:
    """Returns pipx exit code."""
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(f"venv for {package!r} was not found. Was {package!r} installed with pipx?")
    venv.verbose = True
    exit_code = venv.run_pip_get_exit_code(pip_args)
    if exit_code == 0:
        _sync_main_package_metadata_after_runpip_install(venv, pip_args)
    return exit_code
