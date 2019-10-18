import json
from pathlib import Path
from typing import List, Dict, NamedTuple, Any, Optional, TypeVar

from pipx.Venv import PipxVenvMetadata


PIPX_INFO_FILENAME = "pipxrc.json"


class JsonEncoderPipx(json.JSONEncoder):
    def default(self, obj):
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(obj)


def _json_decoder_object_hook(json_dict):
    if json_dict.get("__type__", None) == "Path" and "__Path__" in json_dict:
        return Path(json_dict["__Path__"])
    return json_dict


# Used for consistent types of multiple kinds
Multi = TypeVar("Multi")


class InjectedPackage(NamedTuple):
    pip_args: List[str]
    verbose: bool
    include_apps: bool
    include_dependencies: bool
    force: bool


class InstallOptions(NamedTuple):
    pip_args: Optional[List[str]]
    venv_args: Optional[List[str]]
    include_dependencies: Optional[bool]


class PipxrcInfo:
    def __init__(self):
        self.package_or_url: Optional[str] = None
        self.install: InstallOptions = InstallOptions(
            pip_args=None, venv_args=None, include_dependencies=None
        )
        self.venv_metadata: Optional[PipxVenvMetadata] = None
        self.injected_packages: Optional[Dict[str, InjectedPackage]] = None
        self._pipxrc_version: str = "0.1"

    def to_dict(self) -> Dict[str, Any]:
        venv_metadata: Optional[Dict[str, Any]]
        injected_packages: Optional[Dict[str, Dict[str, Any]]]

        if self.venv_metadata is not None:
            venv_metadata = self.venv_metadata._asdict()
        else:
            venv_metadata = None
        if self.injected_packages is not None:
            injected_packages = {
                k: v._asdict() for (k, v) in self.injected_packages.items()
            }
        else:
            injected_packages = None

        return {
            "package_or_url": self.package_or_url,
            "install": self.install._asdict(),
            "venv_metadata": venv_metadata,
            "injected_packages": injected_packages,
            "pipxrc_version": self._pipxrc_version,
        }

    def from_dict(self, pipxrc_info_dict) -> None:
        self.package_or_url = pipxrc_info_dict["package_or_url"]
        self.install = InstallOptions(**pipxrc_info_dict["install"])
        self.venv_metadata = PipxVenvMetadata(**pipxrc_info_dict["venv_metadata"])
        self.injected_packages = {
            k: InjectedPackage(**v)
            for (k, v) in pipxrc_info_dict["injected_packages"].items()
        }


class Pipxrc:
    def __init__(self, venv_dir: Path, read: bool = True):
        self.venv_dir = venv_dir
        self.pipxrc_info = PipxrcInfo()
        if read:
            self.read()

    def reset(self) -> None:
        self.pipxrc_info = PipxrcInfo()

    def _val_or_default(self, value: Optional[Multi], default: Multi) -> Multi:
        if value is not None:
            return value
        else:
            return default

    def get_package_or_url(self, default: str) -> str:
        return self._val_or_default(self.pipxrc_info.package_or_url, default)

    def get_install_pip_args(self, default: List[str]) -> List[str]:
        return self._val_or_default(self.pipxrc_info.install.pip_args, default)

    def get_install_venv_args(self, default: List[str]) -> List[str]:
        return self._val_or_default(self.pipxrc_info.install.venv_args, default)

    def get_install_include_dependencies(self, default: bool) -> bool:
        return self._val_or_default(
            self.pipxrc_info.install.include_dependencies, default
        )

    def get_venv_metadata(self, default: PipxVenvMetadata) -> PipxVenvMetadata:
        return self._val_or_default(self.pipxrc_info.venv_metadata, default)

    def get_injected_packages(
        self, default: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if self.pipxrc_info.injected_packages is not None:
            injected_packages = []
            for package in self.pipxrc_info.injected_packages:
                package_info = {"package": package}
                package_info.update(
                    self.pipxrc_info.injected_packages[package]._asdict()
                )
                injected_packages.append(package_info)
            return injected_packages
        else:
            return default

    def set_package_or_url(self, package_or_url: str) -> None:
        # TODO 20190923: if package_or_url is a local path, we need to make it
        #   an absolute path
        self.pipxrc_info.package_or_url = package_or_url

    def set_venv_metadata(self, venv_metadata: PipxVenvMetadata) -> None:
        self.pipxrc_info.venv_metadata = venv_metadata

    def set_install_options(
        self, pip_args: List[str], venv_args: List[str], include_dependencies: bool
    ) -> None:
        self.pipxrc_info.install = InstallOptions(
            pip_args=pip_args,
            venv_args=venv_args,
            include_dependencies=include_dependencies,
        )

    def add_injected_package(
        self,
        package: str,
        pip_args: List[str],
        verbose: bool,
        include_apps: bool,
        include_dependencies: bool,
        force: bool,
    ) -> None:
        if self.pipxrc_info.injected_packages is None:
            self.pipxrc_info.injected_packages = {}

        self.pipxrc_info.injected_packages[package] = InjectedPackage(
            pip_args=pip_args,
            verbose=verbose,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            force=force,
        )

    def write(self) -> None:
        # If writing out, make sure injected_packages is not None, so next
        #   successful read of pipxrc does not use default in
        #   get_injected_packages()
        if self.pipxrc_info.injected_packages is None:
            self.pipxrc_info.injected_packages = {}

        # TODO 20190919: raise exception on failure?
        with open(self.venv_dir / PIPX_INFO_FILENAME, "w") as pipxrc_fh:
            json.dump(
                self.pipxrc_info.to_dict(),
                pipxrc_fh,
                indent=4,
                sort_keys=True,
                cls=JsonEncoderPipx,
            )

    def read(self) -> None:
        try:
            with open(self.venv_dir / PIPX_INFO_FILENAME, "r") as pipxrc_fh:
                self.pipxrc_info.from_dict(
                    json.load(pipxrc_fh, object_hook=_json_decoder_object_hook)
                )
        except IOError:  # Reset self.pipxrc_info if problem reading
            self.reset()
            return
