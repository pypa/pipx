import json
import logging
from pathlib import Path
import re
import textwrap
from typing import List, Dict, NamedTuple, Any, Optional

from pipx.Venv import VenvMetadata, Venv
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


def abs_path_if_local(package_or_url: str, venv: Venv, pip_args: List[str]) -> str:
    """Return the absolute path if package_or_url represents a filepath
    and not a pypi package
    """
    pkg_path = Path(package_or_url)
    if not pkg_path.exists():
        # no existing path, must be pypi package or non-existent
        return package_or_url

    # Editable packages are either local or url, non-url must be local.
    # https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs
    if "--editable" in pip_args and pkg_path.exists():
        return str(pkg_path.resolve())

    # https://www.python.org/dev/peps/pep-0508/#names
    valid_pkg_name = bool(
        re.search(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", package_or_url, re.I)
    )
    if not valid_pkg_name:
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
