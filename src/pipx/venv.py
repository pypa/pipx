import logging
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn

if TYPE_CHECKING:
    from subprocess import CompletedProcess

try:
    from importlib.metadata import Distribution, EntryPoint
except ImportError:
    from importlib_metadata import Distribution, EntryPoint  # type: ignore[import-not-found,no-redef]

from packaging.utils import canonicalize_name

from pipx.animate import animate
from pipx.backends import Backend, assert_not_pip_under_uv, env_default_backend, get_backend, resolve_backend_name
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
)
from pipx.venv_inspect import VenvMetadata, inspect_venv

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Keyed on full path so global vs user-local venvs with the same name don't
# collide; deduped per-session because ``upgrade-all --backend uv`` against
# many pip-backed venvs would otherwise repeat the multi-line warning per venv.
_BACKEND_OVERRIDE_WARNED: Final[set[str]] = set()


def reset_backend_override_warnings() -> None:
    # Test-only: production callers never reset this.
    _BACKEND_OVERRIDE_WARNED.clear()


def _resolve_backend_for_venv(
    *,
    root: Path,
    existing: bool,
    metadata_backend: str | None,
    cli_backend: str | None,
    env_backend: str | None,
) -> tuple[str, str]:
    """Apply cli > metadata > env > auto precedence, warning on conflict.

    Pulled out of ``Venv.__init__`` so the precedence rule is unit-testable
    without instantiating a real venv.
    """
    # Existing venvs lock to their recorded backend: ``uv pip install`` against
    # a pip-backed venv leaves it in an inconsistent state. ``pipx reinstall
    # NAME --backend X`` is the supported flip.
    if existing and cli_backend is not None and cli_backend != metadata_backend:
        warning_key = str(root)
        if warning_key not in _BACKEND_OVERRIDE_WARNED:
            _BACKEND_OVERRIDE_WARNED.add(warning_key)
            _LOGGER.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Ignoring --backend={cli_backend} for existing venv {root.name!r}
                    (recorded backend is {metadata_backend!r}). Run
                    `pipx reinstall {root.name} --backend {cli_backend}` to flip the venv.
                    """,
                    subsequent_indent=" " * 4,
                )
            )
        cli_backend = None
    # Direct ``Venv(...)`` callers (including unit tests) won't have threaded
    # ``env_backend`` through; honor ``PIPX_DEFAULT_BACKEND`` so auto-detect
    # doesn't fire when the operator already opted in via env.
    if env_backend is None:
        env_backend = env_default_backend()
    return resolve_backend_name(cli_value=cli_backend, env_value=env_backend, metadata_value=metadata_backend)


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

    def __init__(
        self,
        path: Path,
        *,
        verbose: bool = False,
        python: str = DEFAULT_PYTHON,
        backend: str | None = None,
        env_backend: str | None = None,
    ) -> None:
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
        self._backend_name, self._backend_source = _resolve_backend_for_venv(
            root=self.root,
            existing=self._existing,
            metadata_backend=self.pipx_metadata.backend if self._existing else None,
            cli_backend=backend,
            env_backend=env_backend,
        )
        self._backend: Backend | None = None
        self._uses_shared_libs_cache: bool | None = None

    @property
    def backend(self) -> Backend:
        if self._backend is None:
            self._backend = get_backend(self._backend_name)
        return self._backend

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def backend_source(self) -> str:
        return self._backend_source

    def check_upgrade_shared_libs(self, verbose: bool, pip_args: list[str], force_upgrade: bool = False):
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
            venv_name = f"{self.pipx_metadata.main_package.package}{self.pipx_metadata.main_package.suffix}"
        else:
            venv_name = self.root.name
        return venv_name

    @property
    def uses_shared_libs(self) -> bool:
        if not self._existing:
            return self.backend.needs_shared_libs()
        if self._uses_shared_libs_cache is not None:
            return self._uses_shared_libs_cache
        # Metadata 0.6+ records ``backend`` authoritatively; older recordings
        # (or missing file) fall back to the .pth probe so legacy venvs still
        # report correctly.
        recorded_version = self.pipx_metadata.read_metadata_version
        if recorded_version is not None and recorded_version >= "0.6":
            answer = self.pipx_metadata.backend == "pip"
        else:
            answer = next(self.root.glob(f"**/{PIPX_SHARED_PTH}"), None) is not None
        self._uses_shared_libs_cache = answer
        return answer

    @property
    def package_metadata(self) -> dict[str, PackageInfo]:
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

    def create_venv(self, venv_args: list[str], pip_args: list[str], override_shared: bool = False) -> None:
        """
        override_shared -- Override installing shared libraries to the pipx shared directory (default False)
        """
        _LOGGER.info("Creating virtual environment")
        if override_shared:
            assert_not_pip_under_uv("pip", self._backend_name)
        self.backend.create_venv(
            self.root,
            python=self.python,
            venv_args=venv_args,
            pip_args=pip_args,
            include_pip=override_shared,
            verbose=self.verbose,
        )

        self.pipx_metadata.venv_args = venv_args
        # Persist the chosen backend on disk only when actually creating the venv.
        # Runtime overrides on existing venvs (e.g. `--backend uv pipx upgrade ...`)
        # must not silently flip the recorded backend.
        self.pipx_metadata.backend = self._backend_name
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
            _LOGGER.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Not removing existing venv {self.root} because it
                    was not created in this session
                    """,
                    subsequent_indent=" " * 4,
                )
            )

    def upgrade_packaging_libraries(self, pip_args: list[str]) -> None:
        if self.uses_shared_libs:
            shared_libs.upgrade(pip_args=pip_args, verbose=self.verbose)
            return
        # Short-circuit before instantiating UvBackend so ``upgrade-all`` over
        # uv venvs still works after uv has been uninstalled (the no-op upgrade
        # would have happened anyway).
        if self._backend_name == "uv":
            return
        self.backend.upgrade_packaging_libraries(self.python_path, pip_args, verbose=self.verbose)

    def uninstall_package(self, package: str, was_injected: bool = False):
        try:
            _LOGGER.info("Uninstalling %s", package)
            with animate(f"uninstalling {package}", self.do_animation):
                self.backend.uninstall(
                    venv_root=self.root,
                    venv_python=self.python_path,
                    package=package,
                    verbose=self.verbose,
                )
        except PipxError as e:
            _LOGGER.info(e)
            raise PipxError(f"Error uninstalling {package}.") from None

        if was_injected:
            self.pipx_metadata.injected_packages.pop(package)
            self.pipx_metadata.write()

    def install_package(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        # package_name in package specifier can mismatch URL due to user error
        package_or_url = fix_package_name(package_or_url, package_name)

        # check syntax and clean up spec and pip_args
        (package_or_url, pip_args) = parse_specifier_for_install(package_or_url, pip_args)

        _LOGGER.info("Installing %s", package_descr := full_package_description(package_name, package_or_url))
        with animate(f"installing {package_descr}", self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_or_url],
                pip_args=pip_args,
                verbose=self.verbose,
            )
        if process.returncode:
            raise PipxError(f"Error installing {full_package_description(package_name, package_or_url)}.")

        self.update_package_metadata(
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

    def install_unmanaged_packages(self, requirements: list[str], pip_args: list[str]) -> None:
        """Install packages in the venv, but do not record them in the metadata."""
        _LOGGER.info("Installing %s", package_descr := ", ".join(requirements))
        with animate(f"installing {package_descr}", self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=list(requirements),
                pip_args=pip_args,
                verbose=self.verbose,
            )
        if process.returncode:
            raise PipxError(f"Error installing {', '.join(requirements)}.")

    def install_package_no_deps(self, package_or_url: str, pip_args: list[str]) -> str:
        with animate(f"determining package name from {package_or_url!r}", self.do_animation):
            old_package_set = self.list_installed_packages()
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_or_url],
                pip_args=pip_args,
                no_deps=True,
                log_pip_errors=False,
                verbose=self.verbose,
            )
        if process.returncode:
            raise PipxError(
                f"""
                Cannot determine package name from spec {package_or_url!r}.
                Check package spec for errors.
                """
            )

        installed_packages = self.list_installed_packages() - old_package_set
        if len(installed_packages) == 1:
            package_name = installed_packages.pop()
            _LOGGER.info(f"Determined package name: {package_name}")
        else:
            _LOGGER.info(f"old_package_set = {old_package_set}")
            _LOGGER.info(f"install_packages = {installed_packages}")
            raise PipxError(
                f"""
                Cannot determine package name from spec {package_or_url!r}.
                Check package spec for errors.
                """
            )

        return package_name

    def get_venv_metadata_for_package(self, package_name: str, package_extras: set[str]) -> VenvMetadata:
        data_start = time.time()
        venv_metadata = inspect_venv(package_name, package_extras, self.bin_path, self.python_path, self.man_path)
        _LOGGER.info(f"get_venv_metadata_for_package: {1e3 * (time.time() - data_start):.0f}ms")
        return venv_metadata

    def update_package_metadata(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
        pinned: bool = False,
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
            pinned=pinned,
        )
        if is_main_package:
            self.pipx_metadata.main_package = package_info
        else:
            self.pipx_metadata.injected_packages[package_name] = package_info

        self.pipx_metadata.write()

    def get_python_version(self) -> str:
        return run_subprocess([str(self.python_path), "--version"]).stdout.strip()

    def list_installed_packages(self, not_required: bool = False) -> set[str]:
        return self.backend.list_installed(
            venv_root=self.root,
            venv_python=self.python_path,
            not_required=not_required,
        )

    def _find_entry_point(self, app: str) -> EntryPoint | None:
        if not self.python_path.exists():
            return None
        dists = Distribution.discover(name=self.main_package_name, path=[str(get_site_packages(self.python_path))])
        for dist in dists:
            for ep in dist.entry_points:
                if ep.group == "pipx.run":
                    if ep.name == app:
                        return ep
                    # Try to infer app name from dist's metadata if given
                    # local path
                    if Path(app).exists() and dist.metadata["Name"] == ep.name:
                        return ep
        return None

    def run_app(self, app: str, filename: str, app_args: list[str]) -> NoReturn:
        entry_point = self._find_entry_point(app)

        # No [pipx.run] entry point; default to run console script.
        if entry_point is None:
            exec_app([str(self.bin_path / filename)] + app_args)

        # Evaluate and execute the entry point.
        _LOGGER.info("Using discovered entry point for 'pipx run'")
        module, attr = entry_point.module, entry_point.attr
        code = f"import sys, {module}\nsys.argv[0] = {entry_point.name!r}\nsys.exit({module}.{attr}())\n"
        exec_app([str(self.python_path), "-c", code] + app_args)

    def has_app(self, app: str, filename: str) -> bool:
        if self._find_entry_point(app) is not None:
            return True
        return (self.bin_path / filename).is_file()

    def has_package(self, package_name: str) -> bool:
        return bool(list(Distribution.discover(name=package_name, path=[str(get_site_packages(self.python_path))])))

    def upgrade_package_no_metadata(self, package_name: str, pip_args: list[str]) -> None:
        _LOGGER.info("Upgrading %s", package_descr := full_package_description(package_name, package_name))
        with animate(f"upgrading {package_descr}", self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_name],
                pip_args=pip_args,
                upgrade=True,
                log_pip_errors=False,
                verbose=self.verbose,
            )
        subprocess_post_check(process)

    def upgrade_package(
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        include_dependencies: bool,
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
    ) -> None:
        _LOGGER.info("Upgrading %s", package_descr := full_package_description(package_name, package_or_url))
        with animate(f"upgrading {package_descr}", self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_or_url],
                pip_args=pip_args,
                upgrade=True,
                log_pip_errors=False,
                verbose=self.verbose,
            )
        subprocess_post_check(process)

        self.update_package_metadata(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=suffix,
        )

    def _run_pip(self, cmd: list[str]) -> "CompletedProcess[str]":
        return self.backend.run_raw_pip(
            venv_root=self.root,
            venv_python=self.python_path,
            args=cmd,
            verbose=self.verbose,
        )

    def run_pip_get_exit_code(self, cmd: list[str]) -> ExitCode:
        process = self.backend.run_raw_pip(
            venv_root=self.root,
            venv_python=self.python_path,
            args=cmd,
            capture_stdout=False,
            capture_stderr=False,
            verbose=self.verbose,
        )
        if process.returncode:
            cmd_str = " ".join(str(c) for c in process.args)
            _LOGGER.error(f"{cmd_str!r} failed")
        return ExitCode(process.returncode)


__all__ = [
    "Venv",
    "VenvContainer",
    "reset_backend_override_warnings",
]
