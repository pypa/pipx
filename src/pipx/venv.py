import json
import logging
import pkgutil
import re
import urllib.parse
from pathlib import Path
from typing import Generator, List, NamedTuple, Dict, Set, Optional

from pipx.animate import animate
from pipx.constants import DEFAULT_PYTHON, PIPX_SHARED_PTH
from pipx.pipx_metadata_file import PipxMetadata, PackageInfo
from pipx.shared_libs import shared_libs
from pipx.util import (
    PipxError,
    full_package_description,
    get_site_packages,
    get_venv_paths,
    rmdir,
    run,
    run_subprocess,
    valid_pypi_name,
)


venv_metadata_inspector_raw = pkgutil.get_data("pipx", "venv_metadata_inspector.py")
assert venv_metadata_inspector_raw is not None, (
    "pipx could not find required file venv_metadata_inspector.py. "
    "Please report this error at https://github.com/pipxproject/pipx. Exiting."
)
VENV_METADATA_INSPECTOR = venv_metadata_inspector_raw.decode("utf-8")


class VenvContainer:
    """A collection of venvs managed by pipx.
    """

    def __init__(self, root: Path):
        self._root = root

    def __repr__(self):
        return f"VenvContainer({str(self._root)!r})"

    def __str__(self):
        return str(self._root)

    def iter_venv_dirs(self) -> Generator[Path, None, None]:
        """Iterate venv directories in this container.
        """
        for entry in self._root.iterdir():
            if not entry.is_dir():
                continue
            yield entry

    def get_venv_dir(self, package: str) -> Path:
        """Return the expected venv path for given `package`.
        """
        return self._root.joinpath(package)

    def verify_shared_libs(self):
        for p in self.iter_venv_dirs():
            Venv(p)


class VenvMetadata(NamedTuple):
    apps: List[str]
    app_paths: List[Path]
    apps_of_dependencies: List[str]
    app_paths_of_dependencies: Dict[str, List[Path]]
    package_version: str
    python_version: str


class Venv:
    """Abstraction for a virtual environment with various useful methods for pipx"""

    def __init__(
        self, path: Path, *, verbose: bool = False, python: str = DEFAULT_PYTHON
    ) -> None:
        self.root = path
        self.python = python
        self.bin_path, self.python_path = get_venv_paths(self.root)
        self.pipx_metadata = PipxMetadata(venv_dir=path)
        self.verbose = verbose
        self.do_animation = not verbose
        try:
            self._existing = self.root.exists() and next(self.root.iterdir())
        except StopIteration:
            self._existing = False

        if self._existing and self.uses_shared_libs:
            if shared_libs.is_valid:
                if shared_libs.needs_upgrade:
                    shared_libs.upgrade([], verbose)
            else:
                shared_libs.create([], verbose)

            if not shared_libs.is_valid:
                raise PipxError(
                    f"Error: pipx's shared venv {shared_libs.root} is invalid and "
                    "needs re-installation. To fix this, install or reinstall a "
                    "package. For example,\n"
                    f"  pipx install {self.root.name} --force"
                )

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
            return_dict[
                self.pipx_metadata.main_package.package
            ] = self.pipx_metadata.main_package
        return return_dict

    def create_venv(self, venv_args: List[str], pip_args: List[str]) -> None:
        with animate("creating virtual environment", self.do_animation):
            cmd = [self.python, "-m", "venv", "--without-pip"]
            run(cmd + venv_args + [str(self.root)])
        shared_libs.create(pip_args, self.verbose)
        pipx_pth = get_site_packages(self.python_path) / PIPX_SHARED_PTH
        # write path pointing to the shared libs site-packages directory
        # example pipx_pth location:
        #   ~/.local/pipx/venvs/black/lib/python3.8/site-packages/pipx_shared.pth
        # example shared_libs.site_packages location:
        #   ~/.local/pipx/shared/lib/python3.6/site-packages
        #
        # https://docs.python.org/3/library/site.html
        # A path configuration file is a file whose name has the form 'name.pth'.
        # its contents are additional items (one per line) to be added to sys.path
        pipx_pth.write_text(f"{shared_libs.site_packages}\n", encoding="utf-8")

        self.pipx_metadata.venv_args = venv_args
        self.pipx_metadata.python_version = self.get_python_version()

    def safe_to_remove(self) -> bool:
        return not self._existing

    def remove_venv(self) -> None:
        if self.safe_to_remove():
            rmdir(self.root)
        else:
            logging.warning(
                f"Not removing existing venv {self.root} because "
                "it was not created in this session"
            )

    def upgrade_packaging_libraries(self, pip_args: List[str]) -> None:
        if self.uses_shared_libs:
            shared_libs.upgrade(pip_args, self.verbose)
        else:
            # TODO: setuptools and wheel? Original code didn't bother
            # but shared libs code does.
            self._upgrade_package_no_metadata("pip", pip_args)

    def install_package(
        self,
        package: Optional[str],  # if None, will be determined in this function
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
    ) -> None:

        if pip_args is None:
            pip_args = []
        if package is None:
            # If no package name is supplied, install only main package
            #   first in order to see what its name is
            package = self.install_package_no_deps(package_or_url, pip_args)

        try:
            with animate(
                f"installing {full_package_description(package, package_or_url)}",
                self.do_animation,
            ):
                cmd = ["install"] + pip_args + [package_or_url]
                self._run_pip(cmd)
        except PipxError as e:
            logging.info(e)
            raise PipxError(
                f"Error installing "
                f"{full_package_description(package, package_or_url)}."
            )

        self._update_package_metadata(
            package=package,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=is_main_package,
        )

        # Verify package installed ok
        if self.package_metadata[package].package_version is None:
            raise PipxError(
                f"Unable to install "
                f"{full_package_description(package, package_or_url)}.\n"
                f"Check the name or spec for errors, and verify that it can "
                f"be installed with pip."
            )

    def install_package_no_deps(self, package_or_url: str, pip_args: List[str]) -> str:
        try:
            with animate(
                f"determining package name from {package_or_url!r}", self.do_animation
            ):
                old_package_set = self.list_installed_packages()
                cmd = ["install"] + ["--no-dependencies"] + pip_args + [package_or_url]
                self._run_pip(cmd)
        except PipxError as e:
            logging.info(e)
            raise PipxError(
                f"Cannot determine package name from spec {package_or_url!r}. "
                f"Check package spec for errors."
            )

        installed_packages = self.list_installed_packages() - old_package_set
        if len(installed_packages) == 1:
            package = installed_packages.pop()
            logging.info(f"Determined package name: '{package}'")
        else:
            logging.info(f"old_package_set = {old_package_set}")
            logging.info(f"install_packages = {installed_packages}")
            raise PipxError(
                f"Cannot determine package name from spec {package_or_url!r}. "
                f"Check package spec for errors."
            )

        return package

    def get_venv_metadata_for_package(self, package: str) -> VenvMetadata:
        data = json.loads(
            run_subprocess(
                [
                    self.python_path,
                    "-c",
                    VENV_METADATA_INSPECTOR,
                    package,
                    self.bin_path,
                ],
                capture_stderr=False,
                log_cmd_str=" ".join(
                    [
                        str(self.python_path),
                        "-c",
                        "<contents of venv_metadata_inspector.py>",
                        package,
                        str(self.bin_path),
                    ]
                ),
            ).stdout
        )

        venv_metadata_traceback = data.pop("exception_traceback", None)
        if venv_metadata_traceback is not None:
            logging.error("Internal error with venv metadata inspection.")
            logging.info(
                f"venv_metadata_inspector.py Traceback:\n{venv_metadata_traceback}"
            )

        data["app_paths"] = [Path(p) for p in data["app_paths"]]
        for dep in data["app_paths_of_dependencies"]:
            data["app_paths_of_dependencies"][dep] = [
                Path(p) for p in data["app_paths_of_dependencies"][dep]
            ]

        return VenvMetadata(**data)

    def _update_package_metadata(
        self,
        package: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
    ) -> None:
        venv_package_metadata = self.get_venv_metadata_for_package(package)
        package_info = PackageInfo(
            package=package,
            package_or_url=abs_path_if_local(package_or_url, self, pip_args),
            pip_args=pip_args,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            apps=venv_package_metadata.apps,
            app_paths=venv_package_metadata.app_paths,
            apps_of_dependencies=venv_package_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_package_metadata.app_paths_of_dependencies,
            package_version=venv_package_metadata.package_version,
        )
        if is_main_package:
            self.pipx_metadata.main_package = package_info
        else:
            self.pipx_metadata.injected_packages[package] = package_info

        self.pipx_metadata.write()

    def get_python_version(self) -> str:
        return run_subprocess([str(self.python_path), "--version"]).stdout.strip()

    def pip_search(self, search_term: str, pip_search_args: List[str]) -> str:
        cmd_run = run_subprocess(
            [str(self.python_path), "-m", "pip", "search"]
            + pip_search_args
            + [search_term]
        )
        return cmd_run.stdout.strip()

    def list_installed_packages(self) -> Set[str]:
        cmd_run = run_subprocess(
            [str(self.python_path), "-m", "pip", "list", "--format=json"]
        )
        pip_list = json.loads(cmd_run.stdout.strip())
        return set([x["name"] for x in pip_list])

    def run_app(self, app: str, app_args: List[str]) -> int:
        cmd = [str(self.bin_path / app)] + app_args
        try:
            return run(cmd, check=False)
        except KeyboardInterrupt:
            return 130  # shell code for Ctrl-C

    def _upgrade_package_no_metadata(self, package: str, pip_args: List[str]) -> None:
        with animate(
            f"upgrading {full_package_description(package, package)}", self.do_animation
        ):
            self._run_pip(["install"] + pip_args + ["--upgrade", package])

    def upgrade_package(
        self,
        package: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
    ) -> None:
        with animate(
            f"upgrading {full_package_description(package, package_or_url)}",
            self.do_animation,
        ):
            self._run_pip(["install"] + pip_args + ["--upgrade", package_or_url])

        self._update_package_metadata(
            package=package,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=is_main_package,
        )

    def _run_pip(self, cmd: List[str]) -> int:
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        return run(cmd)


def abs_path_if_local(package_or_url: str, venv: Venv, pip_args: List[str]) -> str:
    """Return the absolute path if package_or_url represents a filepath
    and not a pypi package
    """
    # if valid url leave it untouched
    if urllib.parse.urlparse(package_or_url).scheme:
        return package_or_url

    pkg_path = Path(package_or_url)
    if not pkg_path.exists():
        # no existing path, must be pypi package or non-existent
        return package_or_url

    # Editable packages are either local or url, non-url must be local.
    # https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs
    if "--editable" in pip_args and pkg_path.exists():
        return str(pkg_path.resolve())

    if not valid_pypi_name(package_or_url):
        return str(pkg_path.resolve())

    # If all of the above conditions do not return, we may have used a pypi
    #   package.
    # If we find a pypi package with this name installed, assume we just
    #   installed it.
    pip_search_args: List[str]

    # If user-defined pypi index url, then use it for search
    try:
        arg_i = pip_args.index("--index-url")
    except ValueError:
        pip_search_args = []
    else:
        pip_search_args = pip_args[arg_i : arg_i + 2]

    pip_search_result_str = venv.pip_search(package_or_url, pip_search_args)
    pip_search_results = pip_search_result_str.split("\n")

    # Get package_or_url and following related lines from pip search stdout
    pkg_found = False
    pip_search_found = []
    for pip_search_line in pip_search_results:
        if pkg_found:
            if re.search(r"^\s", pip_search_line):
                pip_search_found.append(pip_search_line)
            else:
                break
        elif pip_search_line.startswith(package_or_url):
            pip_search_found.append(pip_search_line)
            pkg_found = True
    pip_found_str = " ".join(pip_search_found)

    if pip_found_str.startswith(package_or_url) and "INSTALLED" in pip_found_str:
        return package_or_url
    else:
        return str(pkg_path.resolve())
