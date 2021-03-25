import json
import logging
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Union

from pipx.emojis import hazard
from pipx.util import PipxError, pipx_wrap

logger = logging.getLogger(__name__)


PIPX_INFO_FILENAME = "pipx_metadata.json"


class JsonEncoderHandlesPath(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(obj)


def _json_decoder_object_hook(json_dict: Dict[str, Any]) -> Union[Dict[str, Any], Path]:
    if json_dict.get("__type__", None) == "Path" and "__Path__" in json_dict:
        return Path(json_dict["__Path__"])
    return json_dict


class PackageInfo(NamedTuple):
    package: Optional[str]
    package_or_url: Optional[str]
    pip_args: List[str]
    include_dependencies: bool
    include_apps: bool
    apps: List[str]
    app_paths: List[Path]
    apps_of_dependencies: List[str]
    app_paths_of_dependencies: Dict[str, List[Path]]
    package_version: str
    suffix: str = ""


class PipxMetadata:
    # Only change this if file format changes
    __METADATA_VERSION__: str = "0.2"

    def __init__(self, venv_dir: Path, read: bool = True):
        self.venv_dir = venv_dir
        # We init this instance with reasonable fallback defaults for all
        #   members, EXCEPT for those we cannot know:
        #       self.main_package.package=None
        #       self.main_package.package_or_url=None
        #       self.python_version=None
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
            package_version="",
        )
        self.python_version: Optional[str] = None
        self.venv_args: List[str] = []
        self.injected_packages: Dict[str, PackageInfo] = {}

        if read:
            self.read()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_package": self.main_package._asdict(),
            "python_version": self.python_version,
            "venv_args": self.venv_args,
            "injected_packages": {
                name: data._asdict() for (name, data) in self.injected_packages.items()
            },
            "pipx_metadata_version": self.__METADATA_VERSION__,
        }

    def _convert_legacy_metadata(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        if metadata_dict["pipx_metadata_version"] == self.__METADATA_VERSION__:
            return metadata_dict
        elif metadata_dict["pipx_metadata_version"] == "0.1":
            main_package_data = metadata_dict["main_package"]
            if main_package_data["package"] != self.venv_dir.name:
                # handle older suffixed packages gracefully
                main_package_data["suffix"] = self.venv_dir.name.replace(
                    main_package_data["package"], ""
                )
            return metadata_dict
        else:
            raise PipxError(
                f"""
                {self.venv_dir.name}: Unknown metadata version
                {metadata_dict['pipx_metadata_version']}. Perhaps it was
                installed with a later version of pipx.
                """
            )

    def from_dict(self, input_dict: Dict[str, Any]) -> None:
        input_dict = self._convert_legacy_metadata(input_dict)
        self.main_package = PackageInfo(**input_dict["main_package"])
        self.python_version = input_dict["python_version"]
        self.venv_args = input_dict["venv_args"]
        self.injected_packages = {
            f"{name}{data.get('suffix', '')}": PackageInfo(**data)
            for (name, data) in input_dict["injected_packages"].items()
        }

    def _validate_before_write(self) -> None:
        if (
            self.main_package.package is None
            or self.main_package.package_or_url is None
            or not self.main_package.include_apps
        ):
            logger.debug(f"PipxMetadata corrupt:\n{self.to_dict()}")
            raise PipxError("Internal Error: PipxMetadata is corrupt, cannot write.")

    def write(self) -> None:
        self._validate_before_write()
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "w") as pipx_metadata_fh:
                json.dump(
                    self.to_dict(),
                    pipx_metadata_fh,
                    indent=4,
                    sort_keys=True,
                    cls=JsonEncoderHandlesPath,
                )
        except IOError:
            logger.warning(
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
            with open(self.venv_dir / PIPX_INFO_FILENAME, "r") as pipx_metadata_fh:
                self.from_dict(
                    json.load(pipx_metadata_fh, object_hook=_json_decoder_object_hook)
                )
        except IOError:  # Reset self if problem reading
            if verbose:
                logger.warning(
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
