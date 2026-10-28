from __future__ import annotations

__lazy_modules__ = ["packaging.utils", "pipx.commands.common", "pipx.package_specifier", "pipx.util", "pipx.venv"]

from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.commands.common import package_name_from_spec
from pipx.package_specifier import extract_index_options, replace_index_options
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.constants import ExitCode


# runpip forwards to pip or uv pip depending on the backend, so skip the values of either one's install options
_OPTIONS_WITH_VALUE: Final[frozenset[str]] = frozenset({
    "--abi",
    "--all-releases",
    "--allow-insecure-host",
    "--build-constraint",
    "--build-constraints",
    "--cache-dir",
    "--cert",
    "--client-cert",
    "--color",
    "--config-file",
    "--config-setting",
    "--config-settings",
    "--config-settings-package",
    "--constraint",
    "--constraints",
    "--default-index",
    "--default-timeout",
    "--directory",
    "--exclude",
    "--exclude-newer",
    "--exclude-newer-package",
    "--excludes",
    "--exists-action",
    "--extra",
    "--extra-index-url",
    "--find-links",
    "--fork-strategy",
    "--group",
    "--implementation",
    "--index",
    "--index-strategy",
    "--index-url",
    "--keyring-provider",
    "--link-mode",
    "--local-log",
    "--log",
    "--log-file",
    "--no-binary",
    "--no-build-isolation-package",
    "--no-editable-package",
    "--no-sources-package",
    "--only-binary",
    "--only-final",
    "--output-format",
    "--override",
    "--overrides",
    "--platform",
    "--prefix",
    "--prerelease",
    "--prerelease-package",
    "--progress-bar",
    "--project",
    "--proxy",
    "--pypi-url",
    "--python",
    "--python-platform",
    "--python-version",
    "--refresh-package",
    "--reinstall-package",
    "--report",
    "--requirement",
    "--requirements",
    "--requirements-from-script",
    "--resolution",
    "--resume-retries",
    "--retries",
    "--root",
    "--root-user-action",
    "--source",
    "--source-dir",
    "--source-directory",
    "--src",
    "--target",
    "--timeout",
    "--torch-backend",
    "--trusted-host",
    "--upgrade-group",
    "--upgrade-package",
    "--upgrade-strategy",
    "--uploaded-prior-to",
    "--use-deprecated",
    "--use-feature",
    "-C",
    "-P",
    "-b",
    "-c",
    "-f",
    "-i",
    "-p",
    "-r",
    "-t",
})


def _iter_install_specs(pip_args: list[str]) -> list[tuple[str, bool]]:
    if not pip_args or pip_args[0] != "install":
        return []

    specs: list[tuple[str, bool]] = []

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
        if arg in _OPTIONS_WITH_VALUE:
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        specs.append((arg, False))
        index += 1

    return specs


def _updated_main_package_pip_args(
    existing_pip_args: list[str], runpip_args: list[str], *, editable: bool
) -> list[str]:
    pip_args = [arg for arg in existing_pip_args if arg not in {"-e", "--editable"}]
    # the new spec was resolved on the indexes this command named, so upgrade and reinstall must ask the same ones
    if index_args := extract_index_options(runpip_args):
        pip_args = replace_index_options(pip_args, index_args)
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
            pip_args=_updated_main_package_pip_args(main_package.pip_args, pip_args, editable=editable),
            include_dependencies=main_package.include_dependencies,
            include_resources_from=main_package.include_resources_from,
            include_apps=main_package.include_apps,
            is_main_package=True,
            suffix=main_package.suffix,
            pinned=main_package.pinned,
        )
        return


def run_pip(package: str, venv_dir: Path, pip_args: list[str], *, verbose: bool) -> ExitCode:
    """Returns pipx exit code."""
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        msg = f"venv for {package!r} was not found. Was {package!r} installed with pipx?"
        raise PipxError(msg)
    venv.verbose = True
    exit_code = venv.run_pip_get_exit_code(pip_args)
    if exit_code == 0:
        _sync_main_package_metadata_after_runpip_install(venv, pip_args)
    return exit_code


__all__ = [
    "run_pip",
]
