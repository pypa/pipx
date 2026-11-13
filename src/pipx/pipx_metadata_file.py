from __future__ import annotations

__lazy_modules__ = [
    "pathlib",
    "pipx.backends",
    "pipx.package_specifier",
    "pipx.redact",
    "pipx.util",
    "pipx.wrap",
    "tempfile",
]

import json
import logging
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, Final, Self, TypedDict, cast

from pipx.backends import KNOWN_BACKENDS
from pipx.emojis import HAZARD
from pipx.options import ExposureOptions
from pipx.package_specifier import replayable_pip_args
from pipx.redact import redact_url_credentials
from pipx.util import PipxError
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Generator

    from pipx.result import JsonValue

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

#: Name of the file that records a virtual environment's pipx metadata.
PIPX_INFO_FILENAME: Final[str] = "pipx_metadata.json"
# bump only when the file format changes
_METADATA_VERSION: Final[str] = "0.12"


class _RawPackageRecord(TypedDict, total=False):
    package: str | None
    package_or_url: str | None
    pip_args: list[str]
    package_version: str
    expected_apps: list[str]
    lock_file: Path | None
    cooldown_days: int | None
    pinned: bool


class _RawExposure(TypedDict, total=False):
    include_dependencies: bool
    include_apps: bool
    include_resources_from: list[str]
    suffix: str


class _RawResources(TypedDict, total=False):
    apps: list[str]
    app_paths: list[Path]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[Path]]
    man_pages: list[str]  # simplint: ignore[duplicate-code]  # separate metadata types share fields
    man_paths: list[Path]
    man_pages_of_dependencies: list[str]
    man_paths_of_dependencies: dict[str, list[Path]]
    completions: list[str]
    completion_paths: list[Path]
    completions_of_dependencies: list[str]
    completion_paths_of_dependencies: dict[str, list[Path]]


class _RawPackageInfo(_RawPackageRecord, _RawExposure, _RawResources, total=False):
    """A package record in its flat form; not total, as files an older pipx wrote lack some of its keys."""


class _RawMetadata(TypedDict, total=False):
    environment: str | None
    main_package: _RawPackageInfo
    python_version: str | None
    source_interpreter: Path | None
    venv_args: list[str]
    injected_packages: dict[str, _RawPackageInfo]
    backend: str
    exposure_enabled: bool
    pipx_metadata_version: str
    pinned: bool


class _RawSpecVenvEntry(TypedDict):
    metadata: _RawMetadata


# what `pipx list --json` writes and `pipx install-all` reads
class _RawSpecFile(TypedDict, total=False):
    venvs: dict[str, _RawSpecVenvEntry]
    pipx_spec_version: str


class PipxMetadata:
    """The pipx metadata of a virtual environment, saved in ``pipx_metadata.json``.

    :param venv_dir: the directory of the virtual environment.
    :param read: read the metadata file when it exists.
    :ivar venv_dir: the directory of the virtual environment.
    :ivar main_package: the metadata of the package the environment was installed for.
    :ivar environment: the name of the environment, or None.
    :ivar python_version: the Python version of the environment, or None.
    :ivar source_interpreter: the interpreter the environment was created from, or None.
    :ivar venv_args: extra arguments passed when creating the environment.

    :ivar injected_packages: the metadata of the injected packages, keyed by package name.
    :ivar backend: the name of the backend that installs packages.
    :ivar exposure_enabled: whether the apps are exposed.
    :ivar read_metadata_version: the version of the metadata file read, or None until a read succeeds.
    """

    def __init__(self, venv_dir: Path, *, read: bool = True) -> None:
        self.venv_dir = venv_dir
        self.main_package = PackageInfo(
            package=None,
            package_or_url=None,
            pip_args=[],
            exposure=ExposureOptions(),  # exposes the apps, as writing refuses a main package without them
            resources=PackageResources(apps=[], app_paths=[], apps_of_dependencies=[], app_paths_of_dependencies={}),
            package_version="",
        )
        self.environment: str | None = None
        self.python_version: str | None = None
        self.source_interpreter: Path | None = None
        self.venv_args: list[str] = []
        self.injected_packages: dict[str, PackageInfo] = {}
        self.backend: str = "pip"
        self.exposure_enabled: bool = True
        # stays None until a read succeeds, which tells a fresh instance from one holding the values on disk
        self.read_metadata_version: str | None = None

        if read:
            self.read()

    def read(self) -> None:
        """Load the metadata from the file, leaving the current values when the file is missing or unreadable."""
        with (
            suppress(AttributeError, KeyError, OSError, PipxError, TypeError, ValueError),
            (self.venv_dir / PIPX_INFO_FILENAME).open("rb") as pipx_metadata_fh,
        ):
            payload: _RawMetadata = json.load(pipx_metadata_fh, object_hook=_json_decoder_object_hook)
            self.from_dict(payload)

    def from_dict(self, input_dict: _RawMetadata) -> None:
        """Load the metadata from a dictionary, converting the layout of older pipx versions.

        :param input_dict: the metadata as read from the file.
        """
        self._convert_legacy_metadata(input_dict)
        self.environment = input_dict.get("environment")
        self.main_package = self._package_info(input_dict["main_package"])
        self.python_version = input_dict.get("python_version")
        self.source_interpreter = (
            Path(source_interpreter) if (source_interpreter := input_dict.get("source_interpreter")) else None
        )
        # the command line can only record --system-site-packages; anything else came from an edited file and would
        # reach python -m venv, where an extra operand or --clear DIR rewrites a directory outside pipx
        recorded_venv_args: Final[list[str]] = input_dict.get("venv_args", [])
        self.venv_args = [arg for arg in recorded_venv_args if arg == "--system-site-packages"]
        if ignored_venv_args := [arg for arg in recorded_venv_args if arg != "--system-site-packages"]:
            _LOGGER.warning(
                "%s: ignoring recorded venv arguments %s; only --system-site-packages is replayed.",
                self.venv_dir.name,
                " ".join(ignored_venv_args),
            )
        # key by the record's own package name, as Venv.update_package_metadata writes it, so a read-modify-write cycle
        # keeps keys stable and files where an earlier pipx saved a suffixed key (black@1) heal
        self.injected_packages = {
            data.get("package") or name: self._package_info(data)
            for (name, data) in input_dict.get("injected_packages", {}).items()
        }
        # an unknown backend, from an edited file or one a newer pipx wrote, reads as pip so that list and uninstall
        # keep working
        recorded_backend = input_dict.get("backend") or "pip"
        if recorded_backend not in KNOWN_BACKENDS:
            _LOGGER.warning(
                "%s: ignoring unknown recorded backend %r; treating as 'pip'.",
                self.venv_dir.name,
                recorded_backend,
            )
            recorded_backend = "pip"
        self.backend = recorded_backend
        self.exposure_enabled = input_dict["exposure_enabled"]
        self.read_metadata_version = input_dict.get("pipx_metadata_version")

    def _convert_legacy_metadata(self, metadata_dict: _RawMetadata) -> None:
        version: Final[str] = metadata_dict["pipx_metadata_version"]
        if version == "0.4":
            metadata_dict["pinned"] = False
        elif version in {"0.2", "0.3"}:
            metadata_dict["source_interpreter"] = None
        elif version == "0.1":
            main_package_data: Final[_RawPackageInfo] = metadata_dict["main_package"]
            package_name: Final[str | None] = main_package_data["package"]
            if package_name is not None and package_name != self.venv_dir.name:
                # 0.1 recorded no suffix, so take it from the venv name
                main_package_data["suffix"] = self.venv_dir.name.replace(package_name, "")
            metadata_dict["source_interpreter"] = None
        elif version not in {_METADATA_VERSION, "0.11", "0.10", "0.9", "0.8", "0.7", "0.6", "0.5"}:
            msg = f"""
                {self.venv_dir.name}: Unknown metadata version {version}, written
                by a later version of pipx. Upgrade pipx to manage this package.
                """
            raise PipxError(msg)
        # files before 0.6 record no backend
        metadata_dict.setdefault("backend", "pip")
        metadata_dict.setdefault("exposure_enabled", True)
        # an earlier pipx named include_resources_from include_apps_from; PackageInfo takes no such field, so the
        # TypedDict leaves the old key out and the pop goes through an untyped view
        for package_data in (metadata_dict["main_package"], *(metadata_dict.get("injected_packages") or {}).values()):
            raw_package_data = cast("dict[str, Any]", package_data)
            if "include_apps_from" in raw_package_data:
                package_data.setdefault("include_resources_from", raw_package_data.pop("include_apps_from"))

    def _package_info(self, data: _RawPackageInfo) -> PackageInfo:
        return replace(PackageInfo.from_dict(data), pip_args=replayable_pip_args(data["pip_args"], self.venv_dir))

    def write(self) -> None:
        """Save the metadata to the file, replacing it atomically.

        :raises PipxError: when the metadata has no main package, so it cannot be saved.
        """
        if (
            self.main_package.package is None
            or self.main_package.package_or_url is None
            or not self.main_package.exposure.include_apps
        ):
            _LOGGER.debug("PipxMetadata corrupt:\n%s", redact_url_credentials(str(self.to_dict())))
            msg = "Internal Error: PipxMetadata is corrupt, cannot write."
            raise PipxError(msg)
        self._replace_file(
            json.dumps(self.to_dict(), indent=4, sort_keys=True, cls=JsonEncoderHandlesPath).encode("utf-8")
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:  # simplint: ignore[imprecise-annotation]  # list[str] is invariant, so JsonValue rejects it
        """Return the metadata as a dictionary, ready to be written as JSON.

        :returns: the metadata as a dictionary.
        """
        return {
            "environment": self.environment,
            "main_package": self.main_package.to_dict(),
            "python_version": self.python_version,
            "source_interpreter": self.source_interpreter,
            "venv_args": self.venv_args,
            "injected_packages": {name: data.to_dict() for (name, data) in self.injected_packages.items()},
            "backend": self.backend,
            "exposure_enabled": self.exposure_enabled,
            "pipx_metadata_version": _METADATA_VERSION,
        }

    def _replace_file(self, content: bytes) -> None:
        # replace instead of writing through: uv hard-links installed files to its cache
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=self.venv_dir,
                prefix=f".{PIPX_INFO_FILENAME}.",
                suffix=".tmp",
                delete=False,
            ) as pipx_metadata_fh:
                temporary_path = Path(pipx_metadata_fh.name)
                pipx_metadata_fh.write(content)
            temporary_path.replace(self.venv_dir / PIPX_INFO_FILENAME)
        except OSError:
            _LOGGER.warning(
                pipx_wrap(
                    f"""
                    {HAZARD}  Unable to write {PIPX_INFO_FILENAME} to
                    {self.venv_dir}.  This may cause future pipx operations
                    involving {self.venv_dir.name} to fail or behave
                    incorrectly.
                    """,
                    subsequent_indent=" " * 4,
                )
            )
        finally:
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink()

    @contextmanager
    def preserved(self) -> Generator[None, None, None]:
        """Restore the metadata file after the enclosed block when the block changed it.

        Installers unpack wheel data files into the environment, so a package can overwrite the file.

        :yields: nothing, while the enclosed block runs.
        """
        # installers unpack a wheel's data files into the venv root, so any package can ship a file of this name
        before: Final[bytes | None] = self._file_content()
        try:
            yield
        finally:
            if self._file_content() != before:
                if before is None:
                    (self.venv_dir / PIPX_INFO_FILENAME).unlink(missing_ok=True)
                else:
                    self._replace_file(before)

    def _file_content(self) -> bytes | None:
        try:
            return (self.venv_dir / PIPX_INFO_FILENAME).read_bytes()
        except OSError:
            return None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageInfo:
    """Metadata of one package installed in an environment: its spec, its apps, its man pages and its completions.

    :param package: the package name the environment was installed from, or None.
    :param package_or_url: the package specifier or URL the environment was installed from, or None.
    :param pip_args: extra arguments passed to pip.
    :param exposure: which apps and dependencies are exposed.
    :param resources: the apps, man pages and completion scripts of the package and of its dependencies.
    :param package_version: the installed version of the package.
    :param expected_apps: apps the install must expose.
    :param lock_file: the lock file the environment was installed from, or None.
    :param cooldown_days: the cooldown in days applied to the new releases, or None.
    :param pinned: whether the package is pinned.
    """

    package: str | None
    package_or_url: str | None
    pip_args: list[str]
    exposure: ExposureOptions
    resources: PackageResources
    package_version: str
    expected_apps: list[str] = field(default_factory=list)
    lock_file: Path | None = None
    cooldown_days: int | None = None
    pinned: bool = False

    @classmethod
    def from_dict(cls, data: _RawPackageInfo) -> Self:
        """Build the metadata from its flat dictionary form, as the metadata file and ``pipx list --json`` hold it.

        :param data: the flat dictionary.
        :returns: the metadata.
        :raises TypeError: when the dictionary misses a required key or holds an unknown one.
        """
        return cls(
            exposure=ExposureOptions(
                **cast("_RawExposure", {key: value for key, value in data.items() if key in _EXPOSURE_KEYS})
            ),
            resources=PackageResources(
                **cast("_RawResources", {key: value for key, value in data.items() if key in _RESOURCE_KEYS})
            ),
            **cast(
                "_RawPackageRecord",
                {key: value for key, value in data.items() if key not in _EXPOSURE_KEYS | _RESOURCE_KEYS},
            ),
        )

    @property
    def app_paths_to_expose(self) -> list[Path]:
        """Paths of the apps exposed for the package and its included dependencies."""
        return [
            *(self.resources.app_paths if self.exposure.include_apps else ()),
            *self._included_dependency_paths(self.resources.app_paths_of_dependencies),
        ]

    def _included_dependency_paths(self, paths_by_package: dict[str, list[Path]]) -> list[Path]:
        included_packages: Final[set[str]] = set(self.exposure.include_resources_from)
        return [
            path
            for package, paths in paths_by_package.items()
            if self.exposure.include_dependencies or package in included_packages
            for path in paths
        ]

    @property
    def apps_to_expose(self) -> list[str]:
        """Names of the apps exposed for the package and its included dependencies."""
        return [*(self.resources.apps if self.exposure.include_apps else ()), *self.included_dependency_apps]

    @property
    def included_dependency_apps(self) -> list[str]:
        """Names of the apps of the included dependencies."""
        included_names: Final[set[str]] = {
            path.name for path in self._included_dependency_paths(self.resources.app_paths_of_dependencies)
        }
        return [app for app in self.resources.apps_of_dependencies if app in included_names]

    @property
    def man_paths_to_expose(self) -> list[Path]:
        """Paths of the man pages exposed for the package and its included dependencies."""
        return [
            *(self.resources.man_paths if self.exposure.include_apps else ()),
            *self._included_dependency_paths(self.resources.man_paths_of_dependencies),
        ]

    @property
    def man_pages_to_expose(self) -> list[str]:
        """Names of the man pages exposed for the package and its included dependencies."""
        included_names: Final[set[str]] = {
            str(Path(path.parent.name) / path.name)
            for path in self._included_dependency_paths(self.resources.man_paths_of_dependencies)
        }
        return [
            *(self.resources.man_pages if self.exposure.include_apps else ()),
            *(page for page in self.resources.man_pages_of_dependencies if page in included_names),
        ]

    @property
    def completion_paths_to_expose(self) -> list[Path]:
        """Paths of the completions exposed for the package and its included dependencies."""
        return [
            *(self.resources.completion_paths if self.exposure.include_apps else ()),
            *self._included_dependency_paths(self.resources.completion_paths_of_dependencies),
        ]

    @property
    def completions_to_expose(self) -> list[str]:
        """Names of the completions exposed for the package and its included dependencies."""
        included_names: Final[set[str]] = {
            f"{path.parent.parent.name}/{path.parent.name}/{path.name}"
            for path in self._included_dependency_paths(self.resources.completion_paths_of_dependencies)
        }
        return [
            *(self.resources.completions if self.exposure.include_apps else ()),
            *(completion for completion in self.resources.completions_of_dependencies if completion in included_names),
        ]

    def to_dict(
        self,
    ) -> dict[str, Any]:  # simplint: ignore[imprecise-annotation]  # list[str] is invariant, so JsonValue rejects it
        """Return the metadata in its flat dictionary form, as the metadata file and ``pipx list --json`` hold it.

        :returns: the flat dictionary.
        """
        return {
            "package": self.package,
            "package_or_url": self.package_or_url,
            "pip_args": self.pip_args,
            "package_version": self.package_version,
            "expected_apps": self.expected_apps,
            "lock_file": self.lock_file,
            "cooldown_days": self.cooldown_days,
            "pinned": self.pinned,
            **asdict(self.exposure),
            **asdict(self.resources),
        }


def _json_decoder_object_hook(json_dict: dict[str, JsonValue]) -> dict[str, JsonValue] | Path:
    if json_dict.get("__type__") == "Path" and "__Path__" in json_dict:
        return Path(cast("str", json_dict["__Path__"]))
    return json_dict


class JsonEncoderHandlesPath(json.JSONEncoder):
    """JSON encoder that writes a path as an object tagged with its type."""

    def default(
        self,
        o: object,  # simplint: ignore[single-letter-name, imprecise-annotation]  # JSONEncoder override
    ) -> dict[str, str]:
        """Return the JSON form of a path, as a dictionary tagged with its type.

        :param o: the object to encode.
        :returns: the tagged form of a path.
        """
        if isinstance(o, Path):
            return {"__type__": "Path", "__Path__": str(o)}
        return super().default(o)


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageResources:
    """The apps, man pages and completion scripts of a package and of its dependencies.

    :param apps: names of the apps of the package.
    :param app_paths: paths of the apps of the package.
    :param apps_of_dependencies: names of the apps of the dependencies.
    :param app_paths_of_dependencies: paths of the apps of each dependency, keyed by package name.
    :param man_pages: names of the man pages of the package.
    :param man_paths: paths of the man pages of the package.
    :param man_pages_of_dependencies: names of the man pages of the dependencies.
    :param man_paths_of_dependencies: paths of the man pages of each dependency, keyed by package name.
    :param completions: names of the completion scripts of the package.
    :param completion_paths: paths of the completion scripts of the package.
    :param completions_of_dependencies: names of the completion scripts of the dependencies.
    :param completion_paths_of_dependencies: paths of the completion scripts of each dependency, by package name.
    """

    apps: list[str]
    app_paths: list[Path]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[Path]]
    man_pages: list[str] = field(default_factory=list)
    man_paths: list[Path] = field(default_factory=list)
    man_pages_of_dependencies: list[str] = field(default_factory=list)
    man_paths_of_dependencies: dict[str, list[Path]] = field(default_factory=dict)
    completions: list[str] = field(default_factory=list)
    completion_paths: list[Path] = field(default_factory=list)
    completions_of_dependencies: list[str] = field(default_factory=list)
    completion_paths_of_dependencies: dict[str, list[Path]] = field(default_factory=dict)


_EXPOSURE_KEYS: Final[frozenset[str]] = frozenset(item.name for item in fields(ExposureOptions))
_RESOURCE_KEYS: Final[frozenset[str]] = frozenset(item.name for item in fields(PackageResources))


def load_spec_file(path: Path) -> _RawSpecFile:
    """Load a spec file, in which paths are restored from their tagged JSON form.

    :param path: the spec file to load.
    :returns: the content of the file.
    """
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle, object_hook=_json_decoder_object_hook)


__all__ = [
    "PIPX_INFO_FILENAME",
    "JsonEncoderHandlesPath",
    "PackageInfo",
    "PackageResources",
    "PipxMetadata",
    "load_spec_file",
]
