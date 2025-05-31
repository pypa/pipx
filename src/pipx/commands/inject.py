import logging
import os
import re
import sys
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Union

from pipx import paths
from pipx.colors import bold
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import EXIT_CODE_INJECT_ERROR, EXIT_CODE_OK, ExitCode
from pipx.emojis import hazard, stars
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv

logger = logging.getLogger(__name__)

COMMENT_RE = re.compile(r"(^|\s+)#.*$")


def inject_dep(
    venv_dir: Path,
    package_name: Optional[str],
    package_spec: str,
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
    suffix: bool = False,
) -> bool:
    logger.debug("Injecting package %s", package_spec)

    if not venv_dir.exists() or not next(venv_dir.iterdir()):
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into nonexistent Virtual Environment
            {venv_dir.name!r}. Be sure to install the package first with 'pipx
            install {venv_dir.name}' before injecting into it.
            """
        )

    venv = Venv(venv_dir, verbose=verbose)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if not venv.package_metadata:
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into Virtual Environment
            {venv.name!r}. {venv.name!r} has missing internal pipx metadata. It
            was likely installed using a pipx version before 0.15.0.0. Please
            uninstall and install {venv.name!r}, or reinstall-all to fix.
            """
        )

    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.
    if package_name is None:
        package_name = package_name_from_spec(
            package_spec,
            os.fspath(venv.python_path),
            pip_args=pip_args,
            verbose=verbose,
        )

    if not force and venv.has_package(package_name):
        logger.info("Package %s has already been injected", package_name)
        print(
            pipx_wrap(
                f"""
                {hazard} {package_name} already seems to be injected in {venv.name!r}.
                Not modifying existing installation in '{venv_dir}'.
                Pass '--force' to force installation.
                """
            )
        )
        return True

    if suffix:
        venv_suffix = venv.package_metadata[venv.main_package_name].suffix
    else:
        venv_suffix = ""
    venv.install_package(
        package_name=package_name,
        package_or_url=package_spec,
        pip_args=pip_args,
        include_dependencies=include_dependencies,
        include_apps=include_apps,
        is_main_package=False,
        suffix=venv_suffix,
    )
    if include_apps:
        run_post_install_actions(
            venv,
            package_name,
            paths.ctx.bin_dir,
            paths.ctx.man_dir,
            venv_dir,
            include_dependencies,
            force=force,
        )

    print(f"  injected package {bold(package_name)} into venv {bold(venv.name)}")
    print(f"done! {stars}", file=sys.stderr)

    # Any failure to install will raise PipxError, otherwise success
    return True


def inject(
    venv_dir: Path,
    package_name: Optional[str],
    package_specs: Iterable[str],
    requirement_files: Iterable[str],
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
    suffix: bool = False,
) -> ExitCode:
    """Returns pipx exit code."""
    # Combined collection of package specifications
    packages = list(package_specs)
    for filename in requirement_files:
        packages.extend(parse_requirements(filename))

    # Remove duplicates and order deterministically
    packages = sorted(set(packages))

    if not packages:
        raise PipxError("No packages have been specified.")
    logger.info("Injecting packages: %r", packages)

    # Inject packages
    if not include_apps and include_dependencies:
        include_apps = True
    all_success = True
    for dep in packages:
        all_success &= inject_dep(
            venv_dir,
            package_name=None,
            package_spec=dep,
            pip_args=pip_args,
            verbose=verbose,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            force=force,
            suffix=suffix,
        )

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK if all_success else EXIT_CODE_INJECT_ERROR


def parse_requirements(filename: Union[str, os.PathLike]) -> Generator[str, None, None]:
    """
    Extract package specifications from requirements file.

    Return all of the non-empty lines with comments removed.
    """
    # Based on https://github.com/pypa/pip/blob/main/src/pip/_internal/req/req_file.py
    with open(filename) as f:
        for line in f:
            # Strip comments and filter empty lines
            if pkgspec := COMMENT_RE.sub("", line).strip():
                yield pkgspec
