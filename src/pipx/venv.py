import json
import logging
import re
import shutil
import time
from pathlib import Path
from subprocess import CompletedProcess
from typing import Dict, Generator, List, NoReturn, Optional, Set

try:
    from importlib.metadata import Distribution, EntryPoint
except ImportError:
    from importlib_metadata import Distribution, EntryPoint  # type: ignore

from packaging.utils import canonicalize_name

from pipx.animate import animate
from pipx.constants import PIPX_SHARED_PTH, ExitCode
from pipx.emojis import hazard
from pipx.interpreter import DEFAULT_PYTHON
from pipx.package_specifier import (
    fix_package_name,
    get_extras,
    parse_specifier_for_install,
    parse_specifier_for_metadata,
)
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata
from pipx.shared_libs import shared_libs
from pipx.util import (
    PipxError,
    exec_app,
    full_package_description,
    get_site_packages,
    get_venv_paths,
    pipx_wrap,
    rmdir,
    run_subprocess,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)
from pipx.venv_inspect import VenvMetadata, inspect_venv

logger = logging.getLogger(__name__)

_entry_point_value_pattern = re.compile(
    r"""
    ^(?P<module>[\w.]+)\s*
    (:\s*(?P<attr>[\w.]+))?\s*
    (?P<extras>\[.*\])?\s*$
    """,
    re.VERBOSE,
)


class VenvContainer:
    """A collection of venvs managed by pipx."""

    def __init__(self, root: Path):
        self._root = root

    def __repr__(self) -> str:
        return f"VenvContainer({str(self._root)!r})"

    def __str__(self) -> str:
        return str(self._root)

    def iter_venv_dirs(self) -> Generator[Path, None, None]:
        """Iterate venv directories in this container."""
        if not self._root.is_dir():
            return
        for entry in self._root.iterdir():
            if not entry.is_dir():
                continue
            yield entry

    def get_venv_dir(self, package_name: str) -> Path:
        """Return the expected venv path for given `package_name`."""
        return self._root.joinpath(canonicalize_name(package_name))


class Venv:
    """Abstraction for a virtual environment with various useful methods for pipx"""

    def __init__(self, path: Path, *, verbose: bool = False, python: str = DEFAULT_PYTHON) -> None:
        self.root = path
        self.python = python
        self.bin_path, self.python_path, self.man_path = get_venv_paths(self.root)
        self.pipx_metadata = PipxMetadata(venv_dir=path)
        self.verbose = verbose
        self.do_animation = not verbose
        try:
            self._existing = self.root.exists() and bool(next(self.root.iterdir()))
        except StopIteration:
            self._existing = False

    def check_upgrade_shared_libs(self, verbose: bool, pip_args: List[str], force_upgrade: bool = False):
        """
        If necessary, run maintenance tasks to keep the shared libs up-to-date.

        This can trigger `pip install`/`pip install --upgrade` operations,
        so we expect the caller to provide sensible `pip_args`
        ( provided by the user in the current CLI call
        or retrieved from the metadata of a previous installation)
        """
        if self._existing and self.uses_shared_libs:
            if shared_libs.is_valid:
                if force_upgrade or shared_libs.needs_upgrade:
                    shared_libs.upgrade(verbose=verbose, pip_args=pip_args)
            else:
                shared_libs.create(verbose=verbose, pip_args=pip_args)

            if not shared_libs.is_valid:
                raise PipxError(
                    pipx_wrap(
                        f"""
                        Error: pipx's shared venv {shared_libs.root} is invalid
                        and needs re-installation. To fix this, install or
                        reinstall a package. For example:
                        """
                    )
                    + f"\n  pipx install {self.root.name} --force",
                    wrap_message=False,
                )

    @property
    def name(self) -> str:
        if self.pipx_metadata.main_package.package is not None:
            venv_name = f"{self.pipx_metadata.main_package.package}" f"{self.pipx_metadata.main_package.suffix}"
        else:
            venv_name = self.root.name
        return venv_name

    @property
    def uses_shared_libs(self) -> bool:
        if self._existing:
            pth_files = self.root.glob("**/" + PIPX_SHARED_PTH)
            return next(pth_files, None) is not None
        else:
            # always use shared libs when creating a new venv
            return True

    @property
    def package_metadata(self) -> Dict[str, PackageInfo]:
        return_dict = self.pipx_metadata.injected_packages.copy()
        if self.pipx_metadata.main_package.package is not None:
            return_dict[self.pipx_metadata.main_package.package] = self.pipx_metadata.main_package
        return return_dict

    @property
    def main_package_name(self) -> str:
        if self.pipx_metadata.main_package.package is None:
            # This is OK, because if no metadata, we are pipx < v0.15.0.0 and
            #   venv_name==main_package_name
            return self.root.name
        else:
            return self.pipx_metadata.main_package.package

    def create_venv(self, venv_args: List[str], pip_args: List[str], override_shared: bool = False) -> None:
        """
        override_shared -- Override installing shared libraries to the pipx shared directory (default False)
        """
        with animate("creating virtual environment", self.do_animation):
            cmd = [self.python, "-m", "venv"]
            if not override_shared:
                cmd.append("--without-pip")
            venv_process = run_subprocess(cmd + venv_args + [str(self.root)], run_dir=str(self.root))
        subprocess_post_check(venv_process)

        shared_libs.create(verbose=self.verbose, pip_args=pip_args)
        if not override_shared:
            pipx_pth = get_site_packages(self.python_path) / PIPX_SHARED_PTH
            # write path pointing to the shared libs site-packages directory
            # example pipx_pth location:
            #   ~/.local/share/pipx/venvs/black/lib/python3.8/site-packages/pipx_shared.pth
            # example shared_libs.site_packages location:
            #   ~/.local/share/pipx/shared/lib/python3.6/site-packages
            #
            # https://docs.python.org/3/library/site.html
            # A path configuration file is a file whose name has the form 'name.pth'.
            # its contents are additional items (one per line) to be added to sys.path
            pipx_pth.write_text(f"{shared_libs.site_packages}\n", encoding="utf-8")

        self.pipx_metadata.venv_args = venv_args
        self.pipx_metadata.python_version = self.get_python_version()
        source_interpreter = shutil.which(self.python)
        if source_interpreter:
            self.pipx_metadata.source_interpreter = Path(source_interpreter)

    def safe_to_remove(self) -> bool:
        return not self._existing

    def remove_venv(self) -> None:
        if self.safe_to_remove():
            rmdir(self.root)
        else:
            logger.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Not removing existing venv {self.root} because it
                    was not created in this session
                    """,
                    subsequent_indent=" " * 4,
                )
            )

    def upgrade_packaging_libraries(self, pip_args: List[str]) -> None:
        if self.uses_shared_libs:
            shared_libs.upgrade(pip_args=pip_args, verbose=self.verbose)
        else:
            # TODO: setuptools and wheel? Original code didn't bother
            # but shared libs code does.
            self.upgrade_package_no_metadata("pip", pip_args)

    def uninstall_package(self, package: str, was_injected: bool = False):
        try:
            with animate(f"uninstalling {package}", self.do_animation):
                cmd = ["uninstall", "-y"] + [package]
                self._run_pip(cmd)
        except PipxError as e:
            logging.info(e)
            raise PipxError(f"Error uninstalling {package}.") from None

        if was_injected:
            self.pipx_metadata.injected_packages.pop(package)
            self.pipx_metadata.write()

    def install_package(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        # package_name in package specifier can mismatch URL due to user error
        package_or_url = fix_package_name(package_or_url, package_name)

        # check syntax and clean up spec and pip_args
        (package_or_url, pip_args) = parse_specifier_for_install(package_or_url, pip_args)

        with animate(
            f"installing {full_package_description(package_name, package_or_url)}",
            self.do_animation,
        ):
            # do not use -q with `pip install` so subprocess_post_check_pip_errors
            #   has more information to analyze in case of failure.
            cmd = [
                str(self.python_path),
                "-m",
                "pip",
                "--no-input",
                "install",
                *pip_args,
                package_or_url,
            ]
            # no logging because any errors will be specially logged by
            #   subprocess_post_check_handle_pip_error()
            pip_process = run_subprocess(cmd, log_stdout=False, log_stderr=False, run_dir=str(self.root))
        subprocess_post_check_handle_pip_error(pip_process)
        if pip_process.returncode:
            raise PipxError(f"Error installing {full_package_description(package_name, package_or_url)}.")

        self._update_package_metadata(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=suffix,
        )

        # Verify package installed ok
        if self.package_metadata[package_name].package_version is None:
            raise PipxError(
                f"Unable to install "
                f"{full_package_description(package_name, package_or_url)}.\n"
                f"Check the name or spec for errors, and verify that it can "
                f"be installed with pip.",
                wrap_message=False,
            )

    def install_unmanaged_packages(self, requirements: List[str], pip_args: List[str]) -> None:
        """Install packages in the venv, but do not record them in the metadata."""

        # Note: We want to install everything at once, as that lets
        # pip resolve conflicts correctly.
        with animate(f"installing {', '.join(requirements)}", self.do_animation):
            # do not use -q with `pip install` so subprocess_post_check_pip_errors
            #   has more information to analyze in case of failure.
            cmd = [
                str(self.python_path),
                "-m",
                "pip",
                "--no-input",
                "install",
                *pip_args,
                *requirements,
            ]
            # no logging because any errors will be specially logged by
            #   subprocess_post_check_handle_pip_error()
            pip_process = run_subprocess(cmd, log_stdout=False, log_stderr=False, run_dir=str(self.root))
        subprocess_post_check_handle_pip_error(pip_process)
        if pip_process.returncode:
            raise PipxError(f"Error installing {', '.join(requirements)}.")

    def install_package_no_deps(self, package_or_url: str, pip_args: List[str]) -> str:
        with animate(f"determining package name from {package_or_url!r}", self.do_animation):
            old_package_set = self.list_installed_packages()
            cmd = [
                "--no-input",
                "install",
                "--no-dependencies",
                *pip_args,
                package_or_url,
            ]
            pip_process = self._run_pip(cmd)
        subprocess_post_check(pip_process, raise_error=False)
        if pip_process.returncode:
            raise PipxError(
                f"""
                Cannot determine package name from spec {package_or_url!r}.
                Check package spec for errors.
                """
            )

        installed_packages = self.list_installed_packages() - old_package_set
        if len(installed_packages) == 1:
            package_name = installed_packages.pop()
            logger.info(f"Determined package name: {package_name}")
        else:
            logger.info(f"old_package_set = {old_package_set}")
            logger.info(f"install_packages = {installed_packages}")
            raise PipxError(
                f"""
                Cannot determine package name from spec {package_or_url!r}.
                Check package spec for errors.
                """
            )

        return package_name

    def get_venv_metadata_for_package(self, package_name: str, package_extras: Set[str]) -> VenvMetadata:
        data_start = time.time()
        venv_metadata = inspect_venv(package_name, package_extras, self.bin_path, self.python_path, self.man_path)
        logger.info(f"get_venv_metadata_for_package: {1e3*(time.time()-data_start):.0f}ms")
        return venv_metadata

    def _update_package_metadata(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        venv_package_metadata = self.get_venv_metadata_for_package(package_name, get_extras(package_or_url))
        package_info = PackageInfo(
            package=package_name,
            package_or_url=parse_specifier_for_metadata(package_or_url),
            pip_args=pip_args,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            apps=venv_package_metadata.apps,
            app_paths=venv_package_metadata.app_paths,
            apps_of_dependencies=venv_package_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_package_metadata.app_paths_of_dependencies,
            man_pages=venv_package_metadata.man_pages,
            man_paths=venv_package_metadata.man_paths,
            man_pages_of_dependencies=venv_package_metadata.man_pages_of_dependencies,
            man_paths_of_dependencies=venv_package_metadata.man_paths_of_dependencies,
            package_version=venv_package_metadata.package_version,
            suffix=suffix,
        )
        if is_main_package:
            self.pipx_metadata.main_package = package_info
        else:
            self.pipx_metadata.injected_packages[package_name] = package_info

        self.pipx_metadata.write()

    def get_python_version(self) -> str:
        return run_subprocess([str(self.python_path), "--version"]).stdout.strip()

    def list_installed_packages(self, not_required=False) -> Set[str]:
        cmd_run = run_subprocess(
            [str(self.python_path), "-m", "pip", "list", "--format=json"] + (["--not-required"] if not_required else [])
        )
        pip_list = json.loads(cmd_run.stdout.strip())
        return {x["name"] for x in pip_list}

    def _find_entry_point(self, app: str) -> Optional[EntryPoint]:
        if not self.python_path.exists():
            return None
        dists = Distribution.discover(name=self.main_package_name, path=[str(get_site_packages(self.python_path))])
        for dist in dists:
            for ep in dist.entry_points:
                if ep.group == "pipx.run" and ep.name == app:
                    return ep
        return None

    def run_app(self, app: str, filename: str, app_args: List[str]) -> NoReturn:
        entry_point = self._find_entry_point(app)

        # No [pipx.run] entry point; default to run console script.
        if entry_point is None:
            exec_app([str(self.bin_path / filename)] + app_args)

        # Evaluate and execute the entry point.
        # TODO: After dropping support for Python < 3.9, use
        # "entry_point.module" and "entry_point.attr" instead.
        match = _entry_point_value_pattern.match(entry_point.value)
        assert match is not None, "invalid entry point"
        module, attr = match.group("module", "attr")
        code = f"import sys, {module}\n" f"sys.argv[0] = {entry_point.name!r}\n" f"sys.exit({module}.{attr}())\n"
        exec_app([str(self.python_path), "-c", code] + app_args)

    def has_app(self, app: str, filename: str) -> bool:
        if self._find_entry_point(app) is not None:
            return True
        return (self.bin_path / filename).is_file()

    def upgrade_package_no_metadata(self, package_name: str, pip_args: List[str]) -> None:
        with animate(
            f"upgrading {full_package_description(package_name, package_name)}",
            self.do_animation,
        ):
            pip_process = self._run_pip(["--no-input", "install"] + pip_args + ["--upgrade", package_name])
        subprocess_post_check(pip_process)

    def upgrade_package(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        with animate(
            f"upgrading {full_package_description(package_name, package_or_url)}",
            self.do_animation,
        ):
            pip_process = self._run_pip(["--no-input", "install"] + pip_args + ["--upgrade", package_or_url])
        subprocess_post_check(pip_process)

        self._update_package_metadata(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=suffix,
        )

    def _run_pip(self, cmd: List[str]) -> "CompletedProcess[str]":
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        return run_subprocess(cmd, run_dir=str(self.root))

    def run_pip_get_exit_code(self, cmd: List[str]) -> ExitCode:
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        returncode = run_subprocess(cmd, capture_stdout=False, capture_stderr=False).returncode
        if returncode:
            cmd_str = " ".join(str(c) for c in cmd)
            logger.error(f"{cmd_str!r} failed")
        return ExitCode(returncode)
