import json
import logging
import pkgutil
import subprocess
from pathlib import Path
from typing import Dict, List, NamedTuple

from pipx.animate import animate
from pipx.constants import DEFAULT_PYTHON, PIPX_SHARED_PTH, WINDOWS
from pipx.util import (
    PipxError,
    rmdir,
    get_venv_paths,
    get_script_output,
    get_site_packages,
    run,
)
from pipx.SharedLibs import shared_libs


from typing import Generator


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


class PipxVenvMetadata(NamedTuple):
    apps: List[str]
    app_paths: List[Path]
    apps_of_dependencies: List[str]
    app_paths_of_dependencies: Dict[str, List[Path]]
    package_version: str
    python_version: str


venv_metadata_inspector_raw = pkgutil.get_data("pipx", "venv_metadata_inspector.py")
assert venv_metadata_inspector_raw is not None, (
    "pipx could not find required file venv_metadata_inspector.py. "
    "Please report this error at https://github.com/pipxproject/pipx. Exiting."
)
VENV_METADATA_INSPECTOR = venv_metadata_inspector_raw.decode("utf-8")


class Venv:
    """Abstraction for a virtual environment with various useful methods for pipx"""

    def __init__(
        self, path: Path, *, verbose: bool = False, python: str = DEFAULT_PYTHON
    ) -> None:
        self.root = path
        self._python = python
        self.bin_path, self.python_path = get_venv_paths(self.root)
        self.verbose = verbose
        self.do_animation = not verbose
        try:
            self._existing = self.root.exists() and next(self.root.iterdir())
        except StopIteration:
            self._existing = False

        if self._existing and self.uses_shared_libs and not shared_libs.is_valid:
            logging.warning(
                f"Shared libraries not found, but are required for package {self.root.name}. "
                "Attemping to install now."
            )
            shared_libs.create([])
            if shared_libs.is_valid:
                logging.info("Successfully created shared libraries")
            else:
                raise PipxError(
                    f"Error: pipx's shared venv is invalid and "
                    "needs re-installation. To fix this, install or reinstall a "
                    "package. For example,\n"
                    f"  pipx install {self.root.name} --force"
                )

    @property
    def uses_shared_libs(self):
        if self._existing:
            pth_files = self.root.glob("**/" + PIPX_SHARED_PTH)
            return next(pth_files, None) is not None
        else:
            # always use shared libs when creating a new venv
            return True

    def create_venv(self, venv_args: List[str], pip_args: List[str]) -> None:
        with animate("creating virtual environment", self.do_animation):
            cmd = [self._python, "-m", "venv", "--without-pip"]
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
            pipx_pth.write_text(str(shared_libs.site_packages) + "\n", encoding="utf-8")

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
            self.upgrade_package("pip", pip_args)

    def install_package(self, package_or_url: str, pip_args: List[str]) -> None:
        with animate(f"installing package {package_or_url!r}", self.do_animation):
            if pip_args is None:
                pip_args = []
            cmd = ["install"] + pip_args + [package_or_url]
            self._run_pip(cmd)

    def get_venv_metadata_for_package(self, package: str) -> PipxVenvMetadata:

        data = json.loads(
            get_script_output(
                self.python_path, VENV_METADATA_INSPECTOR, package, str(self.bin_path)
            )
        )
        data["app_paths"] = [Path(p) for p in data["app_paths"]]

        data["apps_of_dependencies"] = []
        for dep, raw_paths in data["app_paths_of_dependencies"].items():
            paths = [Path(raw_path) for raw_path in raw_paths]
            data["app_paths_of_dependencies"][dep] = paths
            data["apps_of_dependencies"] += [path.name for path in paths]

        if WINDOWS:
            windows_bin_paths = set()
            for app in data["app_paths"]:
                # windows has additional files staring with the same name that are required
                # to run the app
                for win_exec in app.parent.glob(f"{app.name}*"):
                    windows_bin_paths.add(win_exec)
            data["app_paths"] = list(windows_bin_paths)
        return PipxVenvMetadata(**data)

    def get_python_version(self) -> str:
        return (
            subprocess.run([str(self.python_path), "--version"], stdout=subprocess.PIPE)
            .stdout.decode()
            .strip()
        )

    def run_app(self, app: str, app_args: List[str]):
        cmd = [str(self.bin_path / app)] + app_args
        try:
            return run(cmd, check=False)
        except KeyboardInterrupt:
            pass

    def upgrade_package(self, package_or_url: str, pip_args: List[str]):
        self._run_pip(["install"] + pip_args + ["--upgrade", package_or_url])

    def _run_pip(self, cmd):
        cmd = [self.python_path, "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        return run(cmd)
