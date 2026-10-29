from __future__ import annotations

__lazy_modules__ = [
    "packaging.utils",
    "pathlib",
    "pipx.commands.common",
    "pipx.package_specifier",
    "pipx.util",
    "pipx.venv",
]

from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.commands.common import package_name_from_spec
from pipx.package_specifier import absolute_path_pip_args, extract_index_options, replace_index_options
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
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

# pip expands an unambiguous prefix of a long option; knowing its flags (and uv's flags that prefix a listed option)
# keeps a prefix shared with a flag, or a complete uv flag, from being read as taking a value
_LONG_FLAGS: Final[frozenset[str]] = frozenset({
    "--break-system-packages",
    "--check-build-dependencies",
    "--compile",
    "--debug",
    "--disable-pip-version-check",
    "--dry-run",
    "--force-reinstall",
    "--help",
    "--ignore-installed",
    "--ignore-requires-python",
    "--isolated",
    "--no-build",
    "--no-build-isolation",
    "--no-cache-dir",
    "--no-clean",
    "--no-color",
    "--no-compile",
    "--no-dependencies",
    "--no-deps",
    "--no-editable",
    "--no-index",
    "--no-input",
    "--no-proxy-env",
    "--no-python-version-warning",
    "--no-require-hashes",
    "--no-sources",
    "--no-user",
    "--no-warn-conflicts",
    "--no-warn-script-location",
    "--only-dependencies",
    "--only-deps",
    "--pre",
    "--prefer-binary",
    "--quiet",
    "--refresh",
    "--reinstall",
    "--require-hashes",
    "--require-venv",
    "--require-virtualenv",
    "--upgrade",
    "--use-pep517",
    "--user",
    "--verbose",
    "--version",
})


def _iter_install_specs(pip_args: list[str]) -> list[tuple[str, bool]]:
    if not pip_args or pip_args[0] != "install":
        return []

    specs: list[tuple[str, bool]] = []

    index = 1
    while index < len(pip_args):
        arg = pip_args[index]
        if arg == "-e" or _abbreviates_editable(arg):
            if index + 1 < len(pip_args):
                specs.append((pip_args[index + 1], True))
            index += 2
            continue
        option, separator, value = arg.partition("=")
        if separator and _abbreviates_editable(option):
            specs.append((value, True))
            index += 1
            continue
        if _takes_value(arg):
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        specs.append((arg, False))
        index += 1

    return specs


def _abbreviates_editable(option: str) -> bool:
    # pip reads --edit as --editable, and recording its path as a plain spec would drop the editable install on upgrade
    return (
        option.startswith("--")
        and "--editable".startswith(option)
        and not any(known.startswith(option) for known in _OPTIONS_WITH_VALUE | _LONG_FLAGS)
    )


def _takes_value(arg: str) -> bool:
    if arg in _OPTIONS_WITH_VALUE:
        return True
    if not arg.startswith("--") or "=" in arg or arg in _LONG_FLAGS:
        return False
    candidates = {option for option in _OPTIONS_WITH_VALUE | _LONG_FLAGS if option.startswith(arg)}
    return bool(candidates) and candidates <= _OPTIONS_WITH_VALUE


def _updated_main_package_pip_args(
    existing_pip_args: list[str], runpip_args: list[str], *, editable: bool
) -> list[str]:
    pip_args = [arg for arg in existing_pip_args if arg not in {"-e", "--editable"}]
    # the new spec was resolved on the indexes this command named, so upgrade and reinstall must ask the same ones;
    # pip read relative paths from the caller's directory, while a recorded relative path is read against the venv
    if index_args := extract_index_options(runpip_args):
        pip_args = replace_index_options(pip_args, absolute_path_pip_args(index_args, Path.cwd()))
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
