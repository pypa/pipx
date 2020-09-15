import json
import logging
import textwrap
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from pipx.util import PipxError

PIPX_INFO_FILENAME = "pipx_metadata.json"


class JsonEncoderHandlesPath(json.JSONEncoder):
    def default(self, obj):
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(obj)


def _json_decoder_object_hook(json_dict):
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

    def reset(self) -> None:
        # We init this instance with reasonable fallback defaults for all
        #   members, EXCEPT for those we cannot know:
        #       self.main_package.package_or_url=None
        #       self.venv_metadata.package_or_url=None
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
        self.python_version = None
        self.venv_args = []
        self.injected_packages = {}

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

    def from_dict(self, input_dict: Dict[str, Any]) -> None:
        main_package_data = input_dict["main_package"]
        if main_package_data["package"] != self.venv_dir.name:
            # handle older suffixed packages gracefully
            main_package_data["suffix"] = self.venv_dir.name.replace(
                main_package_data["package"], ""
            )

        self.main_package = PackageInfo(**main_package_data)
        self.python_version = input_dict["python_version"]
        self.venv_args = input_dict["venv_args"]
        self.injected_packages = {
            f"{name}{data.get('suffix', '')}": PackageInfo(**data)
            for (name, data) in input_dict["injected_packages"].items()
        }

    def _validate_before_write(self):
        if (
            self.main_package.package is None
            or self.main_package.package_or_url is None
            or not self.main_package.include_apps
        ):
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
            logging.warning(
                textwrap.fill(
                    f"Unable to write {PIPX_INFO_FILENAME} to {self.venv_dir}. "
                    f"This may cause future pipx operations involving "
                    f"{self.venv_dir.name} to fail or behave incorrectly.",
                    width=79,
                )
            )
            pass

    def read(self, verbose: bool = False) -> None:
        # TODO: if no file is present or old version, try to deduce what a modern
        #       metadata would look like and recreate
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "r") as pipx_metadata_fh:
                self.from_dict(
                    json.load(pipx_metadata_fh, object_hook=_json_decoder_object_hook)
                )
        except IOError:  # Reset self if problem reading
            if verbose:
                logging.warning(
                    textwrap.fill(
                        f"Unable to read {PIPX_INFO_FILENAME} in {self.venv_dir}. "
                        f"This may cause this or future pipx operations involving "
                        f"{self.venv_dir.name} to fail or behave incorrectly.",
                        width=79,
                    )
                )
            return
