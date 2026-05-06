import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final, TypedDict

from pipx.backends._base import KNOWN_BACKENDS
from pipx.emojis import hazard
from pipx.util import PipxError, pipx_wrap

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


PIPX_INFO_FILENAME = "pipx_metadata.json"


class _RawPackageInfo(TypedDict, total=False):
    """JSON-on-disk shape for :class:`PackageInfo`.

    ``total=False`` because the legacy-metadata migration runs against dumps
    from older pipx versions that lacked some keys.
    """

    package: str | None
    package_or_url: str | None
    pip_args: list[str]
    include_dependencies: bool
    include_apps: bool
    apps: list[str]
    app_paths: list[Path]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[Path]]
    package_version: str
    man_pages: list[str]
    man_paths: list[Path]
    man_pages_of_dependencies: list[str]
    man_paths_of_dependencies: dict[str, list[Path]]
    suffix: str
    pinned: bool


class _RawMetadata(TypedDict, total=False):
    """JSON-on-disk shape for ``pipx_metadata.json``."""

    main_package: _RawPackageInfo
    python_version: str | None
    source_interpreter: Path | None
    venv_args: list[str]
    injected_packages: dict[str, _RawPackageInfo]
    backend: str
    pipx_metadata_version: str
    pinned: bool


class _RawSpecVenvEntry(TypedDict):
    metadata: _RawMetadata


class _RawSpecFile(TypedDict, total=False):
    # Wire format produced by ``pipx list --json`` and consumed by ``install-all``.
    venvs: dict[str, _RawSpecVenvEntry]
    pipx_spec_version: str


class JsonEncoderHandlesPath(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(obj)


def _json_decoder_object_hook(json_dict: dict[str, Any]) -> dict[str, Any] | Path:
    if json_dict.get("__type__") == "Path" and "__Path__" in json_dict:
        return Path(json_dict["__Path__"])
    return json_dict


@dataclass(frozen=True)
class PackageInfo:
    package: str | None
    package_or_url: str | None
    pip_args: list[str]
    include_dependencies: bool
    include_apps: bool
    apps: list[str]
    app_paths: list[Path]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[Path]]
    package_version: str
    man_pages: list[str] = field(default_factory=list)
    man_paths: list[Path] = field(default_factory=list)
    man_pages_of_dependencies: list[str] = field(default_factory=list)
    man_paths_of_dependencies: dict[str, list[Path]] = field(default_factory=dict)
    suffix: str = ""
    pinned: bool = False


class PipxMetadata:
    # Only change this if file format changes
    # V0.1 -> original version
    # V0.2 -> Improve handling of suffixes
    # V0.3 -> Add man pages fields
    # V0.4 -> Add source interpreter
    # V0.5 -> Add pinned
    # V0.6 -> Add backend (pip|uv)
    __METADATA_VERSION__: str = "0.6"

    def __init__(self, venv_dir: Path, read: bool = True):
        self.venv_dir = venv_dir
        # Reasonable defaults for everything except the fields the caller
        # populates from the install spec (package, package_or_url, python_version).
        self.main_package = PackageInfo(
            package=None,
            package_or_url=None,
            pip_args=[],
            include_dependencies=False,
            include_apps=True,  # always True for main_package
            apps=[],
            app_paths=[],
            apps_of_dependencies=[],
            app_paths_of_dependencies={},
            man_pages=[],
            man_paths=[],
            man_pages_of_dependencies=[],
            man_paths_of_dependencies={},
            package_version="",
        )
        self.python_version: str | None = None
        self.source_interpreter: Path | None = None
        self.venv_args: list[str] = []
        self.injected_packages: dict[str, PackageInfo] = {}
        self.backend: str = "pip"
        # ``None`` until ``read()`` succeeds; lets callers tell a fresh
        # instance from one with authoritative on-disk values.
        self.read_metadata_version: str | None = None

        if read:
            self.read()

    def to_dict(self) -> dict[str, Any]:
        # Plain dict over _RawMetadata: asdict() returns dict[str, Any] and
        # consumers serialise straight to JSON.
        return {
            "main_package": asdict(self.main_package),
            "python_version": self.python_version,
            "source_interpreter": self.source_interpreter,
            "venv_args": self.venv_args,
            "injected_packages": {name: asdict(data) for (name, data) in self.injected_packages.items()},
            "backend": self.backend,
            "pipx_metadata_version": self.__METADATA_VERSION__,
        }

    def _convert_legacy_metadata(self, metadata_dict: _RawMetadata) -> _RawMetadata:
        version = metadata_dict["pipx_metadata_version"]
        if version in (self.__METADATA_VERSION__, "0.5"):
            pass
        elif version == "0.4":
            metadata_dict["pinned"] = False
        elif version in ("0.2", "0.3"):
            metadata_dict["source_interpreter"] = None
        elif version == "0.1":
            main_package_data = metadata_dict["main_package"]
            package_name = main_package_data["package"]
            if package_name is not None and package_name != self.venv_dir.name:
                # handle older suffixed packages gracefully
                main_package_data["suffix"] = self.venv_dir.name.replace(package_name, "")
            metadata_dict["source_interpreter"] = None
        else:
            raise PipxError(
                f"""
                {self.venv_dir.name}: Unknown metadata version {version}.
                Perhaps it was installed with a later version of pipx.
                """
            )
        # ``backend`` is absent from any pre-0.6 dump; default once here.
        metadata_dict.setdefault("backend", "pip")
        return metadata_dict

    def from_dict(self, input_dict: _RawMetadata) -> None:
        input_dict = self._convert_legacy_metadata(input_dict)
        self.main_package = PackageInfo(**input_dict["main_package"])
        self.python_version = input_dict.get("python_version")
        source_interpreter_raw = input_dict.get("source_interpreter")
        self.source_interpreter = Path(source_interpreter_raw) if source_interpreter_raw else None
        self.venv_args = input_dict.get("venv_args", [])
        self.injected_packages = {
            f"{name}{data.get('suffix', '')}": PackageInfo(**data)
            for (name, data) in input_dict.get("injected_packages", {}).items()
        }
        # Permissive: an unknown ``backend`` (manual edit, post-downgrade
        # dump from a newer pipx) falls back to pip with a warning so
        # ``pipx list`` / ``pipx uninstall`` keep working. Strict validation
        # still fires on write via :func:`pipx.backends.resolve_backend_name`.
        recorded_backend = input_dict.get("backend") or "pip"
        if recorded_backend not in KNOWN_BACKENDS:
            _LOGGER.warning(
                "%s: ignoring unknown recorded backend %r; treating as 'pip'.",
                self.venv_dir.name,
                recorded_backend,
            )
            recorded_backend = "pip"
        self.backend = recorded_backend
        self.read_metadata_version = input_dict.get("pipx_metadata_version")

    def _validate_before_write(self) -> None:
        if (
            self.main_package.package is None
            or self.main_package.package_or_url is None
            or not self.main_package.include_apps
        ):
            _LOGGER.debug(f"PipxMetadata corrupt:\n{self.to_dict()}")
            raise PipxError("Internal Error: PipxMetadata is corrupt, cannot write.")

    def write(self) -> None:
        self._validate_before_write()
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "w", encoding="utf-8") as pipx_metadata_fh:
                json.dump(
                    self.to_dict(),
                    pipx_metadata_fh,
                    indent=4,
                    sort_keys=True,
                    cls=JsonEncoderHandlesPath,
                )
        except OSError:
            _LOGGER.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Unable to write {PIPX_INFO_FILENAME} to
                    {self.venv_dir}.  This may cause future pipx operations
                    involving {self.venv_dir.name} to fail or behave
                    incorrectly.
                    """,
                    subsequent_indent=" " * 4,
                )
            )

    def read(self, verbose: bool = False) -> None:
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "rb") as pipx_metadata_fh:
                payload: _RawMetadata = json.load(pipx_metadata_fh, object_hook=_json_decoder_object_hook)
                self.from_dict(payload)
        except OSError:  # Reset self if problem reading
            if verbose:
                _LOGGER.warning(
                    pipx_wrap(
                        f"""
                        {hazard}  Unable to read {PIPX_INFO_FILENAME} in
                        {self.venv_dir}.  This may cause this or future pipx
                        operations involving {self.venv_dir.name} to fail or
                        behave incorrectly.
                        """,
                        subsequent_indent=" " * 4,
                    )
                )
            return


def load_spec_file(path: Path) -> "_RawSpecFile":
    # Round-trips Path values through :class:`JsonEncoderHandlesPath`'s hook.
    with open(path, encoding="utf-8") as handle:
        payload: _RawSpecFile = json.load(handle, object_hook=_json_decoder_object_hook)
    return payload


__all__ = [
    "PIPX_INFO_FILENAME",
    "JsonEncoderHandlesPath",
    "PackageInfo",
    "PipxMetadata",
    "load_spec_file",
]
