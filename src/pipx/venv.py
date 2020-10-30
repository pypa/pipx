import json
import logging
import pkgutil
import sys  # TODO: debug
import time  # TODO: debug
from pathlib import Path
from typing import Dict, Generator, List, NamedTuple, Set

from pipx.animate import animate
from pipx.constants import PIPX_SHARED_PTH
from pipx.interpreter import DEFAULT_PYTHON
from pipx.package_specifier import (
    append_extras,
    fix_package_name,
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
    rmdir,
    run_subprocess,
    run_verify,
)

venv_metadata_inspector_raw = pkgutil.get_data("pipx", "venv_metadata_inspector.py")
assert venv_metadata_inspector_raw is not None, (
    "pipx could not find required file venv_metadata_inspector.py. "
    "Please report this error at https://github.com/pipxproject/pipx. Exiting."
)
VENV_METADATA_INSPECTOR = venv_metadata_inspector_raw.decode("utf-8")

# TODO: debugging
venv_metadata_inspector_legacy_raw = pkgutil.get_data(
    "pipx", "venv_metadata_inspector_legacy.py"
)
assert venv_metadata_inspector_legacy_raw is not None, (
    "pipx could not find required file venv_metadata_inspector_legacy.py. "
    "Please report this error at https://github.com/pipxproject/pipx. Exiting."
)
VENV_METADATA_INSPECTOR_LEGACY = venv_metadata_inspector_legacy_raw.decode("utf-8")


class VenvContainer:
    """A collection of venvs managed by pipx."""

    def __init__(self, root: Path):
        self._root = root

    def __repr__(self):
        return f"VenvContainer({str(self._root)!r})"

    def __str__(self):
        return str(self._root)

    def iter_venv_dirs(self) -> Generator[Path, None, None]:
        """Iterate venv directories in this container."""
        for entry in self._root.iterdir():
            if not entry.is_dir():
                continue
            yield entry

    def get_venv_dir(self, package: str) -> Path:
        """Return the expected venv path for given `package`."""
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

    @property
    def main_package_name(self) -> str:
        if self.pipx_metadata.main_package.package is None:
            # This is OK, because if no metadata, we are pipx < v0.15.0.0 and
            #   venv_name==main_package_name
            return self.root.name
        else:
            return self.pipx_metadata.main_package.package

    def create_venv(self, venv_args: List[str], pip_args: List[str]) -> None:
        with animate("creating virtual environment", self.do_animation):
            cmd = [self.python, "-m", "venv", "--without-pip"]
            run_verify(cmd + venv_args + [str(self.root)])
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
        package: str,
        package_or_url: str,
        pip_args: List[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        if pip_args is None:
            pip_args = []

        # package name in package specifier can mismatch URL due to user error
        package_or_url = fix_package_name(package_or_url, package)

        # check syntax and clean up spec and pip_args
        (package_or_url, pip_args) = parse_specifier_for_install(
            package_or_url, pip_args
        )

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
            suffix=suffix,
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
            logging.info(f"Determined package name: {package}")
        else:
            logging.info(f"old_package_set = {old_package_set}")
            logging.info(f"install_packages = {installed_packages}")
            raise PipxError(
                f"Cannot determine package name from spec {package_or_url!r}. "
                f"Check package spec for errors."
            )

        return package

    # TODO: debugging
    def _debug_compare_metadata(self, data, data_old):
        problem = False
        for field in data_old:
            problem_field = False
            if isinstance(data_old[field], list):
                if len(set(data[field])) != len(data[field]):
                    print(
                        f"\nDuplicate entries inside of list for {field}:",
                        file=sys.stderr,
                    )
                    print(f"    new: {data[field]}", file=sys.stderr)
                    problem_field = True
                    problem = True
                if set(data[field]) != set(data_old[field]):
                    print(f"\nData Inconsistency for {field}:", file=sys.stderr)
                    print(f"    new: {data[field]}", file=sys.stderr)
                    print(f"    old: {data_old[field]}", file=sys.stderr)
                    problem_field = True
                    problem = True
            elif isinstance(data_old[field], dict):
                problem_dict = False
                new_keys = sorted(data[field].keys())
                old_keys = sorted(data_old[field].keys())
                for new_key in new_keys:
                    old_key_compare = "???"
                    if new_key in old_keys:
                        old_key_compare = new_key
                    else:
                        for old_key in old_keys:
                            if old_key.lower().startswith(new_key):
                                old_key_compare = old_key
                                break
                    if old_key_compare == "???":
                        # print(f"Data Inconsistency for {field}:", file=sys.stderr)
                        # print(
                        #    f"    new[{new_key}]: {data[field][new_key]}",
                        #    file=sys.stderr,
                        # )
                        # print(f"    old[{new_key}]: ???", file=sys.stderr)
                        problem_dict = True
                        break
                    elif set(data[field][new_key]) != set(
                        data_old[field][old_key_compare]
                    ):
                        # print(f"Data Inconsistency for {field}:", file=sys.stderr)
                        # print(
                        #    f"    new[{new_key}]: {data[field][new_key]}",
                        #    file=sys.stderr,
                        # )
                        # print(
                        #    f"    old[{old_key_compare}]: {data_old[field][old_key_compare]}",
                        #    file=sys.stderr,
                        # )
                        problem_dict = True
                        break
                if problem_dict:
                    print(f"\nData Inconsistency for {field}:", file=sys.stderr)
                    print(f"NEW DATA[{field}]:")
                    print(json.dumps(data[field], sort_keys=True, indent=4))
                    print(f"OLD DATA[{field}]:")
                    print(json.dumps(data_old[field], sort_keys=True, indent=4))
                    problem_field = True
                    problem = True
            else:
                if data.get(field, None) != data_old.get(field, None):
                    print(f"\nData Inconsistency for {field}:", file=sys.stderr)
                    print(f"    new: {data.get(field, None)}", file=sys.stderr)
                    print(f"    old: {data_old.get(field, None)}", file=sys.stderr)
                    problem_field = True
                    problem = True
            if not problem_field:
                print(f"\nFIELD: {field}")
                print(f"    new: {data.get(field, None)}")
                print(f"    old: {data_old.get(field, None)}")
        if problem:
            raise PipxError("Problem with new venv_metadata_inspector.")

    def get_venv_metadata_for_package(self, package: str) -> VenvMetadata:
        data_start = time.time()  # TODO: debugging
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
        logging.info(
            f"venv_metadata_inspector: {1e3*(time.time()-data_start):.0f}ms"
        )  # TODO: debugging

        # TODO: debugging
        data_start = time.time()
        data_legacy = json.loads(
            run_subprocess(
                [
                    self.python_path,
                    "-c",
                    VENV_METADATA_INSPECTOR_LEGACY,
                    package,
                    self.bin_path,
                ],
                capture_stderr=False,
                log_cmd_str=" ".join(
                    [
                        str(self.python_path),
                        "-c",
                        "<contents of venv_metadata_inspector_legacy.py>",
                        package,
                        str(self.bin_path),
                    ]
                ),
            ).stdout
        )
        logging.info(
            f"venv_metadata_inspector_legacy: {1e3*(time.time()-data_start):.0f}ms"
        )
        self._debug_compare_metadata(data, data_legacy)

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
        suffix: str = "",
    ) -> None:
        venv_package_metadata = self.get_venv_metadata_for_package(
            append_extras(package, package_or_url)
        )
        package_info = PackageInfo(
            package=package,
            package_or_url=parse_specifier_for_metadata(package_or_url),
            pip_args=pip_args,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            apps=venv_package_metadata.apps,
            app_paths=venv_package_metadata.app_paths,
            apps_of_dependencies=venv_package_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_package_metadata.app_paths_of_dependencies,
            package_version=venv_package_metadata.package_version,
            suffix=suffix,
        )
        if is_main_package:
            self.pipx_metadata.main_package = package_info
        else:
            self.pipx_metadata.injected_packages[package] = package_info

        self.pipx_metadata.write()

    def get_python_version(self) -> str:
        return run_subprocess([str(self.python_path), "--version"]).stdout.strip()

    def list_installed_packages(self) -> Set[str]:
        cmd_run = run_subprocess(
            [str(self.python_path), "-m", "pip", "list", "--format=json"]
        )
        pip_list = json.loads(cmd_run.stdout.strip())
        return set([x["name"] for x in pip_list])

    def run_app(self, app: str, app_args: List[str]) -> None:
        exec_app([str(self.bin_path / app)] + app_args)

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
        suffix: str = "",
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
            suffix=suffix,
        )

    def _run_pip(self, cmd: List[str]) -> None:
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        run_verify(cmd)
