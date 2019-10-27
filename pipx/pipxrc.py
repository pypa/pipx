import json
import logging
from pathlib import Path
import textwrap
from typing import List, Dict, NamedTuple, Any, Optional

# from pipx.Venv import VenvMetadata, Venv
from pipx.util import PipxError, VenvMetadata


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
    package_or_url: Optional[str]
    pip_args: List[str]
    include_dependencies: bool
    include_apps: bool


class PipxMetadata:
    def __init__(self, venv_dir: Path, read: bool = True):
        self.venv_dir = venv_dir
        self.main_package = PackageInfo(
            package_or_url=None,
            pip_args=[],
            include_dependencies=False,
            include_apps=True,  # always True for main_package
        )
        self.venv_metadata: Optional[VenvMetadata] = None
        self.venv_args: List[str] = []
        self.injected_packages: List[PackageInfo] = []

        # Only change this if file format changes
        self._pipx_metadata_version: str = "0.1"

        if read:
            self.read()

    def reset(self) -> None:
        # We init this instance with reasonable fallback defaults for all
        #   members, EXCEPT for those we cannot know:
        #       self.main_package.package_or_url=None
        #       self.venv_metadata.package_or_url=None
        self.main_package = PackageInfo(
            package_or_url=None,
            pip_args=[],
            include_dependencies=False,
            include_apps=True,  # always True for main_package
        )
        self.venv_metadata = None
        self.venv_args = []
        self.injected_packages = []

    def to_dict(self) -> Dict[str, Any]:
        venv_metadata: Optional[Dict[str, Any]]
        if self.venv_metadata is not None:
            venv_metadata = self.venv_metadata._asdict()
        else:
            venv_metadata = None

        return {
            "main_package": self.main_package._asdict(),
            "venv_metadata": venv_metadata,
            "venv_args": self.venv_args,
            "injected_packages": [x._asdict() for x in self.injected_packages],
            "pipx_metadata_version": self._pipx_metadata_version,
        }

    def from_dict(self, input_dict: Dict[str, Any]) -> None:
        venv_metadata: Optional[VenvMetadata]
        if input_dict["venv_metadata"] is not None:
            venv_metadata = VenvMetadata(**input_dict["venv_metadata"])
        else:
            venv_metadata = None

        self.main_package = PackageInfo(**input_dict["main_package"])
        self.venv_metadata = venv_metadata
        self.venv_args = input_dict["venv_args"]
        self.injected_packages = [
            PackageInfo(**x) for x in input_dict["injected_packages"]
        ]

    def validate_before_write(self):
        if (
            self.venv_metadata is None
            or self.main_package.package_or_url is None
            or not self.main_package.include_apps
        ):
            raise PipxError("Internal Error: PipxMetadata is corrupt, cannot write.")

    def write(self) -> None:
        self.validate_before_write()
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

    def read(self) -> None:
        # TODO 20191026: make verbose argument, only show warning if verbose
        #   and make it less alarming.
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "r") as pipx_metadata_fh:
                self.from_dict(
                    json.load(pipx_metadata_fh, object_hook=_json_decoder_object_hook)
                )
        except IOError:  # Reset self if problem reading
            logging.warning(
                textwrap.fill(
                    f"Unable to read {PIPX_INFO_FILENAME} in {self.venv_dir}. "
                    f"This may cause this or future pipx operations involving "
                    f"{self.venv_dir.name} to fail or behave incorrectly.",
                    width=79,
                )
            )
            self.reset()
            return
