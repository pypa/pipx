from __future__ import annotations

__lazy_modules__ = [
    "packaging.utils",
    "pathlib",
    "pipx.backends",
    "pipx.interpreter",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.requires_python",
    "pipx.script",
    "pipx.shared_libs",
    "pipx.util",
    "shutil",
]

import logging
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Iterable, Iterator, Sequence
    from importlib.metadata import Distribution, EntryPoint
    from subprocess import CompletedProcess

    from filelock import BaseFileLock
    from packaging.utils import NormalizedName

    from pipx.venv_inspect import VenvMetadata

from packaging.utils import InvalidName, canonicalize_name
from packaging.version import Version

from pipx.animate import STDERR_IS_TTY, animate
from pipx.backends import (
    Backend,
    OutdatedPackage,
    assert_not_pip_under_uv,
    env_default_backend,
    get_backend,
    resolve_backend_name,
)
from pipx.constants import PIPX_SHARED_PTH, ExitCode
from pipx.emojis import hazard
from pipx.interpreter import get_default_python
from pipx.package_specifier import (
    fix_package_name,
    get_extras,
    package_spec_satisfied,
    parse_specifier_for_install,
    parse_specifier_for_metadata,
    valid_pypi_name,
)
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata
from pipx.requires_python import IncompatiblePythonError, rejected_constraint
from pipx.script import installable_script, local_script
from pipx.shared_libs import (
    DISABLE_SHARED_LIBS_AUTO_UPGRADE,
    shared_libs,
    shared_libs_auto_upgrade_disabled,
)
from pipx.util import (
    InstalledNameMismatchError,
    PipxError,
    exec_app,
    full_package_description,
    get_site_packages,
    get_venv_paths,
    pipx_wrap,
    redact_url_credentials,
    rmdir,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_BACKEND_METADATA_VERSION: Final[Version] = Version("0.6")

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

    def __init__(self, root: Path) -> None:
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

    def iter_locked_venv_dirs(
        self, venv_dirs: Iterable[Path], *, allow_permission_error: bool = False
    ) -> Generator[Path, None, None]:
        for venv_dir in venv_dirs:
            lock = self.venv_lock(venv_dir)
            try:
                lock.acquire()
            except PermissionError:
                if not allow_permission_error:
                    raise
                if venv_dir.is_dir():
                    yield venv_dir
                continue

            try:
                if venv_dir.is_dir():
                    yield venv_dir
            finally:
                lock.release()

    def venv_lock(self, venv_dir: Path) -> BaseFileLock:
        from filelock import FileLock  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

        self._root.mkdir(parents=True, exist_ok=True)
        return FileLock(self._root / f".{canonicalize_name(venv_dir.name)}.lock")


class Venv:  # ruff:ignore[too-many-public-methods]  # single facade over a pipx-managed virtual environment; splitting would scatter its state
    """Abstraction for a virtual environment with various useful methods for pipx"""

    def __init__(
        self,
        path: Path,
        *,
        verbose: bool = False,
        python: str | None = None,
        backend: str | None = None,
        env_backend: str | None = None,
    ) -> None:
        self.root = path
        self.python = python or get_default_python()
        self.bin_path, self.python_path, self.man_path = get_venv_paths(self.root)
        self.pipx_metadata = PipxMetadata(venv_dir=path)
        self.verbose = verbose
        # a terminal lets pip and uv draw their own download bar, which stands in for the spinner
        self.show_progress = not verbose and STDERR_IS_TTY
        self.do_animation = not verbose and not self.show_progress
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
        self._site_packages: list[Path] | None = None
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

    def check_upgrade_shared_libs(self, *, verbose: bool, pip_args: list[str]) -> None:
        """
        If necessary, run maintenance tasks to keep the shared libs up-to-date.

        This can trigger `pip install`/`pip install --upgrade` operations,
        so we expect the caller to provide sensible `pip_args`
        ( provided by the user in the current CLI call
        or retrieved from the metadata of a previous installation)
        """
        if self._existing and self.uses_shared_libs:
            if shared_libs.is_valid:
                if shared_libs_auto_upgrade_disabled():
                    _LOGGER.info(
                        "Skipping shared libs auto-upgrade because %s is set.", DISABLE_SHARED_LIBS_AUTO_UPGRADE
                    )
                elif shared_libs.needs_upgrade:
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
        if recorded_version is not None and Version(recorded_version) >= _BACKEND_METADATA_VERSION:
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
            #   the venv name is the main package name
            return self.root.name
        return self.pipx_metadata.main_package.package

    def create_venv(self, venv_args: list[str], pip_args: list[str], *, override_shared: bool = False) -> None:
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
        self._site_packages = None

        self.pipx_metadata.venv_args = venv_args
        # Persist the chosen backend on disk only when actually creating the venv.
        # Runtime overrides on existing venvs (e.g. `--backend uv pipx upgrade ...`)
        # must not silently flip the recorded backend.
        self.pipx_metadata.backend = self._backend_name
        # update_package_metadata records it from the package inspection, sparing a `python --version` run
        self.pipx_metadata.python_version = None
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
        # check_upgrade_shared_libs owns the shared pip, refreshing it at most every 30 days unless disabled
        if self.uses_shared_libs:
            return
        # Short-circuit before instantiating UvBackend so ``upgrade-all`` over
        # uv venvs still works after uv has been uninstalled (the no-op upgrade
        # would have happened anyway).
        if self._backend_name == "uv":
            return
        self.backend.upgrade_packaging_libraries(self.python_path, pip_args, verbose=self.verbose)

    def uninstall_packages(self, *packages: str, was_injected: bool = False) -> None:
        for package in packages:
            _LOGGER.info("Uninstalling %s", package)
        names = ", ".join(packages)
        try:
            with animate(f"uninstalling {names}", do_animation=self.do_animation):
                self.backend.uninstall(
                    venv_root=self.root,
                    venv_python=self.python_path,
                    packages=packages,
                    verbose=self.verbose,
                )
        except PipxError as e:
            _LOGGER.info(e)
            msg = f"Error uninstalling {names}."
            raise PipxError(msg) from None

        if was_injected:
            for package in packages:
                self.pipx_metadata.injected_packages.pop(package)
            self.pipx_metadata.write()

    def install_package(  # ruff:ignore[too-many-arguments]  # flat install API mirroring the CLI's install options
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        *,
        include_dependencies: bool,
        include_resources_from: Sequence[str],
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
        install_only_pip_args: list[str] | None = None,
        expected_apps: Sequence[str] | None = None,
        lock_file: Path | None = None,
        pinned: bool | None = None,
        cooldown_days: int | None = None,
    ) -> VenvMetadata:
        # a script path can also read as a PyPI name (bare.py) or as extras (dir[1]/app.py), so pin it to the file
        if (script := local_script(package_or_url)) is not None:
            package_or_url = str(script)
        # package_name in package specifier can mismatch URL due to user error
        package_or_url = fix_package_name(package_or_url, package_name)

        # check syntax and clean up spec and pip_args
        (package_or_url, pip_args) = parse_specifier_for_install(package_or_url, pip_args)
        install_pip_args: Final[list[str]] = self._with_cooldown(
            [*(install_only_pip_args or []), *pip_args], cooldown_days
        )

        with installable_script(package_name, package_or_url, tuple(expected_apps or ())) as install_spec:
            if lock_file is None:
                _LOGGER.info("Installing %s", package_descr := full_package_description(package_name, package_or_url))
                with animate(f"installing {package_descr}", do_animation=self.do_animation):
                    process = self.backend.install(
                        venv_root=self.root,
                        venv_python=self.python_path,
                        requirements=[install_spec],
                        pip_args=install_pip_args,
                        log_pip_errors=False,
                        verbose=self.verbose,
                        progress=self.show_progress,
                    )
                if process.returncode:
                    # the backend refuses the interpreter and installs nothing, so its complaint is the only place the
                    # constraint appears; uv ignores upper bounds, which the caller catches from the metadata instead
                    if constraint := rejected_constraint(process.stderr or ""):
                        raise IncompatiblePythonError(constraint)
                    subprocess_post_check_handle_pip_error(
                        process, tool_name=self.backend_name, streamed=self.verbose or self.show_progress
                    )
                    msg = f"Error installing {full_package_description(package_name, package_or_url)}."
                    raise PipxError(msg, backend_output=_as_displayed(process.stderr or process.stdout or ""))
            else:
                self._install_locked_package(package_name, install_spec, lock_file, install_pip_args)

        if not self.has_package(package_name) and (installed := self._name_installed_from(package_or_url)) is not None:
            raise InstalledNameMismatchError(installed)
        venv_metadata: Final[VenvMetadata] = self.update_package_metadata(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_resources_from=include_resources_from,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=suffix,
            expected_apps=expected_apps,
            lock_file=lock_file,
            pinned=pinned,
            cooldown_days=cooldown_days,
        )

        # Verify package installed ok
        if self.package_metadata[package_name].package_version is None:
            msg = (
                f"Unable to install "
                f"{full_package_description(package_name, package_or_url)}.\n"
                f"Check the name or spec for errors, and verify that it can "
                f"be installed with pip."
            )
            raise PipxError(
                msg,
                wrap_message=False,
            )
        return venv_metadata

    def _name_installed_from(self, package_or_url: str) -> str | None:
        import json  # ruff:ignore[import-outside-top-level]  # slows startup
        from urllib.parse import urlsplit  # ruff:ignore[import-outside-top-level]  # slows startup
        from urllib.request import url2pathname  # ruff:ignore[import-outside-top-level]  # slows startup

        # installers record the local path a distribution came from (PEP 610), naming what the spec built
        locations: Final[dict[str, str]] = {
            url2pathname(urlsplit(json.loads(direct_url).get("url", "")).path): distribution.name
            for distribution in self._distributions()
            if (direct_url := distribution.read_text("direct_url.json")) is not None
        }
        return locations.get(package_or_url) or locations.get(package_or_url.rpartition("[")[0])

    def _install_locked_package(
        self,
        package_name: str,
        package_or_url: str,
        lock_file: Path,
        pip_args: list[str],
    ) -> None:
        _LOGGER.info("Installing packages from %s", lock_file)
        with animate(f"installing packages from {lock_file.name}", do_animation=self.do_animation):
            process = self.backend.install_lock(
                venv_root=self.root,
                venv_python=self.python_path,
                lock_file=lock_file,
                pip_args=[argument for argument in pip_args if argument != "--editable"],
                verbose=self.verbose,
                progress=self.show_progress,
            )
        if process.returncode:
            msg = f"Error installing packages from {lock_file}."
            raise PipxError(msg)

        if valid_pypi_name(package_or_url) is None:
            package_descr = full_package_description(package_name, package_or_url)
            with animate(f"installing {package_descr}", do_animation=self.do_animation):
                process = self.backend.install(
                    venv_root=self.root,
                    venv_python=self.python_path,
                    requirements=[package_or_url],
                    pip_args=pip_args,
                    no_deps=True,
                    verbose=self.verbose,
                    progress=self.show_progress,
                )
            if process.returncode:
                msg = f"Error installing {full_package_description(package_name, package_or_url)}."
                raise PipxError(msg)
        elif (distribution := next(self._distributions(package_name), None)) is None:
            msg = f"Lock file {lock_file} does not contain {package_name}."
            raise PipxError(msg)
        elif not package_spec_satisfied(package_or_url, package_name, distribution.version, package_or_url):
            msg = (
                f"Lock file {lock_file} provides {package_name} {distribution.version}, "
                f"which does not satisfy {redact_url_credentials(package_or_url)}."
            )
            raise PipxError(msg)

        process = self.backend.run_raw_pip(
            venv_root=self.root,
            venv_python=self.python_path,
            args=["check"],
            verbose=self.verbose,
        )
        if process.returncode:
            error = (process.stdout or process.stderr or "dependency check failed").strip()
            msg = f"Lock file {lock_file} does not satisfy {package_name}: {error}"
            raise PipxError(msg, wrap_message=False)

    def install_unmanaged_packages(
        self,
        requirements: list[str],
        pip_args: list[str],
        cooldown_days: int | None = None,
    ) -> None:
        """Install packages in the venv, but do not record them in the metadata."""
        _LOGGER.info("Installing %s", package_descr := ", ".join(requirements))
        with animate(f"installing {package_descr}", do_animation=self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=list(requirements),
                pip_args=self._with_cooldown(pip_args, cooldown_days),
                verbose=self.verbose,
                progress=self.show_progress,
            )
        if process.returncode:
            msg = f"Error installing {', '.join(requirements)}."
            raise PipxError(msg)

    def install_package_no_deps(
        self,
        package_or_url: str,
        pip_args: list[str],
        cooldown_days: int | None = None,
    ) -> str:
        with animate(
            f"determining package name from {redact_url_credentials(package_or_url)!r}", do_animation=self.do_animation
        ):
            old_package_set = self.list_installed_packages()
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_or_url],
                pip_args=self._with_cooldown(pip_args, cooldown_days),
                no_deps=True,
                log_pip_errors=False,
                verbose=self.verbose,
                progress=self.show_progress,
            )
        if process.returncode:
            error_output = (process.stderr or process.stdout or "").strip()
            if constraint := rejected_constraint(error_output):
                raise IncompatiblePythonError(constraint)
            if error_output and not (self.verbose or self.show_progress):
                raise PipxError(error_output, wrap_message=False)
            msg = f"""
                Error determining package name from spec {redact_url_credentials(package_or_url)!r}.
                See installer output for details.
                """
            raise PipxError(msg, backend_output=_as_displayed(error_output))

        installed_packages = self.list_installed_packages() - old_package_set
        if len(installed_packages) == 1:
            package_name = installed_packages.pop()
            _LOGGER.info("Determined package name: %s", package_name)
        else:
            _LOGGER.info("old_package_set = %s", old_package_set)
            _LOGGER.info("install_packages = %s", installed_packages)
            msg = f"""
                Cannot determine package name from spec {redact_url_credentials(package_or_url)!r}.
                Check package spec for errors.
                """
            raise PipxError(msg)

        return package_name

    def get_venv_metadata_for_package(self, package_name: str, package_extras: set[str]) -> VenvMetadata:
        from pipx.venv_inspect import inspect_venv  # ruff:ignore[import-outside-top-level]  # pulls in packaging.requirements, slows startup

        data_start = time.time()
        venv_metadata = inspect_venv(package_name, package_extras, self.bin_path, self.python_path, self.man_path)
        _LOGGER.info("get_venv_metadata_for_package: %.0fms", 1e3 * (time.time() - data_start))
        return venv_metadata

    def update_package_metadata(  # ruff:ignore[too-many-arguments]  # writes the full PackageInfo record from the CLI's install options
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        *,
        include_dependencies: bool,
        include_resources_from: Sequence[str],
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
        pinned: bool | None = None,
        expected_apps: Sequence[str] | None = None,
        lock_file: Path | None = None,
        cooldown_days: int | None = None,
    ) -> VenvMetadata:
        venv_package_metadata = self.get_venv_metadata_for_package(package_name, get_extras(package_or_url))
        if self.pipx_metadata.python_version is None:
            self.pipx_metadata.python_version = venv_package_metadata.python_version
        if expected_apps is None:
            expected_apps = (
                self.package_metadata[package_name].expected_apps if package_name in self.package_metadata else ()
            )
        if lock_file is None:
            lock_file = self.package_metadata[package_name].lock_file if package_name in self.package_metadata else None
        included_dependencies: Final[list[str]] = list(
            dict.fromkeys(canonicalize_name(name) for name in include_resources_from)
        )
        available_dependencies: Final[set[str]] = (
            venv_package_metadata.app_paths_of_dependencies.keys()
            | venv_package_metadata.man_paths_of_dependencies.keys()
        )
        missing_dependencies: Final[list[str]] = sorted(set(included_dependencies) - available_dependencies)
        if missing_dependencies:
            msg = (
                f"Cannot expose apps from {', '.join(missing_dependencies)} for package {package_name}. "
                "Dependencies with apps or manual pages: "
                f"{', '.join(sorted(available_dependencies)) or 'none'}."
            )
            raise PipxError(msg)
        if cooldown_days is None:
            cooldown_days = (
                self.package_metadata[package_name].cooldown_days if package_name in self.package_metadata else None
            )
        if pinned is None:
            pinned = self.package_metadata[package_name].pinned if package_name in self.package_metadata else False
        package_info = PackageInfo(
            package=package_name,
            package_or_url=parse_specifier_for_metadata(package_or_url),
            pip_args=pip_args,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            include_resources_from=included_dependencies,
            apps=venv_package_metadata.apps,
            app_paths=venv_package_metadata.app_paths,
            apps_of_dependencies=venv_package_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_package_metadata.app_paths_of_dependencies,
            man_pages=venv_package_metadata.man_pages,
            man_paths=venv_package_metadata.man_paths,
            man_pages_of_dependencies=venv_package_metadata.man_pages_of_dependencies,
            man_paths_of_dependencies=venv_package_metadata.man_paths_of_dependencies,
            completions=venv_package_metadata.completions,
            completion_paths=venv_package_metadata.completion_paths,
            completions_of_dependencies=venv_package_metadata.completions_of_dependencies,
            completion_paths_of_dependencies=venv_package_metadata.completion_paths_of_dependencies,
            package_version=venv_package_metadata.package_version,
            expected_apps=list(dict.fromkeys(expected_apps)),
            lock_file=lock_file,
            cooldown_days=cooldown_days,
            suffix=suffix,
            pinned=pinned,
        )
        if is_main_package:
            self.pipx_metadata.main_package = package_info
        else:
            self.pipx_metadata.injected_packages[package_name] = package_info

        self.pipx_metadata.write()
        return venv_package_metadata

    def list_installed_packages(self, *, not_required: bool = False) -> set[str]:
        return self.backend.list_installed(
            venv_root=self.root,
            venv_python=self.python_path,
            not_required=not_required,
        )

    def list_outdated_packages(self, index_args: list[str], packages: Collection[str]) -> tuple[OutdatedPackage, ...]:
        # pip and uv query the index for every installed distribution unless told to exclude it
        return self.backend.list_outdated(
            venv_root=self.root,
            venv_python=self.python_path,
            index_args=index_args,
            exclude=sorted(self._installed_distribution_names().difference(packages)),
        )

    def _installed_distribution_names(self) -> set[str]:
        # the directory name carries the distribution name, so a broken METADATA file cannot fail the listing
        site_packages: Final[list[Path]] = list(self.site_packages)
        if (shared_pth := site_packages[0] / PIPX_SHARED_PTH).is_file():
            site_packages.extend(Path(line) for line in shared_pth.read_text().splitlines())
        return {
            name
            for directory in site_packages
            for pattern in ("*.dist-info", "*.egg-info")
            for path in directory.glob(pattern)
            if (name := _distribution_name(path))
        }

    @property
    def site_packages(self) -> list[Path]:
        if self._site_packages is None:
            self._site_packages = get_site_packages(self.python_path)
        return self._site_packages

    def _distributions(self, name: str | None = None) -> Iterator[Distribution]:
        from importlib.metadata import Distribution  # ruff:ignore[import-outside-top-level]  # slows startup

        return iter(Distribution.discover(name=name, path=[str(path) for path in self.site_packages]))

    def _find_entry_point(self, app: str, group: str) -> EntryPoint | None:
        if not self.python_path.exists():
            return None
        for dist in self._distributions(self.main_package_name):
            for ep in dist.entry_points:
                if ep.group == group:
                    if ep.name == app:
                        return ep
                    # Local project paths do not identify an app, so accept their matching pipx.run entry point.
                    if group == "pipx.run" and Path(app).exists() and dist.metadata["Name"] == ep.name:
                        return ep
        return None

    def run_app(
        self,
        app: str,
        filename: str,
        app_args: list[str],
        *,
        python_args: list[str],
    ) -> NoReturn:
        entry_point = self._find_entry_point(app, "pipx.run")
        if entry_point is None and python_args:
            entry_point = self._find_entry_point(app, "console_scripts")

        if entry_point is None:
            if python_args:
                msg = f"Cannot pass Python arguments because {app!r} is not a Python entry point."
                raise PipxError(msg)
            exec_app([str(self.bin_path / filename), *app_args])

        _LOGGER.info("Using discovered entry point for 'pipx run'")
        code = (
            "import sys\nfrom importlib.metadata import EntryPoint\n"
            f"sys.argv[0] = {entry_point.name!r}\n"
            f"sys.exit(EntryPoint(name={entry_point.name!r}, value={entry_point.value!r}, "
            f"group={entry_point.group!r}).load()())\n"
        )
        exec_app([str(self.python_path), *python_args, "-c", code, *app_args])

    def has_app(self, app: str, filename: str) -> bool:
        if self._find_entry_point(app, "pipx.run") is not None:
            return True
        return (self.bin_path / filename).is_file()

    def has_package(self, package_name: str) -> bool:
        return next(self._distributions(package_name), None) is not None

    def upgrade_package_no_metadata(
        self,
        package_name: str,
        pip_args: list[str],
        cooldown_days: int | None = None,
    ) -> None:
        _LOGGER.info("Upgrading %s", package_descr := full_package_description(package_name, package_name))
        with animate(f"upgrading {package_descr}", do_animation=self.do_animation):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[package_name],
                pip_args=self._with_cooldown(pip_args, cooldown_days),
                upgrade=True,
                log_pip_errors=False,
                verbose=self.verbose,
                progress=self.show_progress,
            )
        subprocess_post_check(process)

    def upgrade_package(  # ruff:ignore[too-many-arguments]  # flat upgrade API mirroring the CLI's upgrade options
        self,
        package_name: str,
        package_or_url: str,
        pip_args: list[str],
        *,
        include_dependencies: bool,
        include_resources_from: Sequence[str],
        include_apps: bool,
        is_main_package: bool,
        suffix: str = "",
        upgrade_only_pip_args: list[str] | None = None,
        expected_apps: Sequence[str] | None = None,
        cooldown_days: int | None = None,
    ) -> None:
        _LOGGER.info("Upgrading %s", package_descr := full_package_description(package_name, package_or_url))
        with (
            installable_script(package_name, package_or_url, tuple(expected_apps or ())) as install_spec,
            animate(f"upgrading {package_descr}", do_animation=self.do_animation),
        ):
            process = self.backend.install(
                venv_root=self.root,
                venv_python=self.python_path,
                requirements=[install_spec],
                pip_args=self._with_cooldown([*(upgrade_only_pip_args or []), *pip_args], cooldown_days),
                upgrade=True,
                log_pip_errors=False,
                verbose=self.verbose,
                progress=self.show_progress,
            )
        subprocess_post_check(process)

        self.update_package_metadata(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_resources_from=include_resources_from,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=suffix,
            expected_apps=expected_apps,
            cooldown_days=cooldown_days,
        )

    def _with_cooldown(self, pip_args: list[str], cooldown_days: int | None) -> list[str]:
        return [*pip_args, *self.backend.cooldown_args(cooldown_days)]

    def _run_pip(self, cmd: list[str]) -> CompletedProcess[str]:
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
            _LOGGER.error("%r failed", redact_url_credentials(" ".join(str(c) for c in process.args)))
        return ExitCode(process.returncode)


def _as_displayed(output: str) -> str:
    # a progress bar redraws its line after each carriage return, so a terminal keeps only the text after the last one
    return "\n".join(line.rpartition("\r")[2].rstrip() for line in output.split("\n")).strip()


def _distribution_name(metadata_dir: Path) -> NormalizedName | None:
    # an interrupted pip leaves ``~name-1.0.dist-info`` behind, and uv rejects such a name as an ``--exclude`` value
    try:
        return canonicalize_name(metadata_dir.name.partition("-")[0], validate=True)
    except InvalidName:
        return None


__all__ = [
    "Venv",
    "VenvContainer",
    "reset_backend_override_warnings",
]
