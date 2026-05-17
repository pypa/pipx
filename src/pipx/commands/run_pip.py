from pathlib import Path
from typing import Final

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.package_specifier import parse_specifier_for_metadata
from pipx.util import PipxError
from pipx.venv import Venv

_PIP_INSTALL_OPTIONS_WITH_ARGUMENT: Final[set[str]] = {
    "--abi",
    "--cache-dir",
    "--cert",
    "--client-cert",
    "--config-settings",
    "--constraint",
    "--editable",
    "--exists-action",
    "--extra-index-url",
    "--find-links",
    "--global-option",
    "--group",
    "--implementation",
    "--index-url",
    "--keyring-provider",
    "--no-binary",
    "--only-binary",
    "--platform",
    "--prefix",
    "--progress-bar",
    "--proxy",
    "--python",
    "--python-version",
    "--report",
    "--requirement",
    "--root",
    "--root-user-action",
    "--src",
    "--target",
    "--timeout",
    "--trusted-host",
    "--upgrade-strategy",
}
_PIP_INSTALL_SHORT_OPTIONS_WITH_ARGUMENT: Final[set[str]] = {"-C", "-c", "-e", "-f", "-i", "-r", "-t"}


def _iter_requirement_args(pip_args: list[str]) -> list[str]:
    if not pip_args or pip_args[0] != "install":
        return []

    requirements = []
    skip_next = False
    for arg in pip_args[1:]:
        if skip_next:
            skip_next = False
            continue

        if arg == "--":
            continue

        if arg.startswith("--"):
            option, has_value, _value = arg.partition("=")
            if not has_value and option in _PIP_INSTALL_OPTIONS_WITH_ARGUMENT:
                skip_next = True
            continue

        if arg.startswith("-") and arg != "-":
            if arg in _PIP_INSTALL_SHORT_OPTIONS_WITH_ARGUMENT:
                skip_next = True
            continue

        requirements.append(arg)

    return requirements


def _main_package_install_spec(pip_args: list[str], main_package: str | None) -> str | None:
    if main_package is None:
        return None

    canonical_main_package = canonicalize_name(main_package)
    for requirement_arg in _iter_requirement_args(pip_args):
        try:
            requirement = Requirement(requirement_arg)
        except InvalidRequirement:
            continue

        if canonicalize_name(requirement.name) == canonical_main_package:
            return parse_specifier_for_metadata(requirement_arg)

    return None


def _refresh_main_package_metadata(venv: Venv, pip_args: list[str]) -> None:
    main_package_metadata = venv.pipx_metadata.main_package
    package_or_url = _main_package_install_spec(pip_args, main_package_metadata.package)
    if package_or_url is None:
        return

    metadata_pip_args = [arg for arg in main_package_metadata.pip_args if arg not in {"--editable", "-e"}]
    venv.update_package_metadata(
        package_name=str(main_package_metadata.package),
        package_or_url=package_or_url,
        pip_args=metadata_pip_args,
        include_dependencies=main_package_metadata.include_dependencies,
        include_apps=main_package_metadata.include_apps,
        is_main_package=True,
        suffix=main_package_metadata.suffix,
        pinned=main_package_metadata.pinned,
    )


def run_pip(package: str, venv_dir: Path, pip_args: list[str], verbose: bool) -> ExitCode:
    """Returns pipx exit code."""
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(f"venv for {package!r} was not found. Was {package!r} installed with pipx?")
    venv.verbose = True
    exit_code = venv.run_pip_get_exit_code(pip_args)
    if exit_code == EXIT_CODE_OK:
        _refresh_main_package_metadata(venv, pip_args)
    return exit_code
