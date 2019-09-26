import copy
import json
from pathlib import Path
from typing import List, Dict, Any

from pipx.Venv import PipxVenvMetadata


class JsonEncoderPipx(json.JSONEncoder):
    def default(self, obj):
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(obj)


def _json_decoder_object_hook(json_dict):
    if json_dict.get("__type__", None) == "Path" and "__Path__" in json_dict:
        return Path(json_dict["__Path__"])
    if (
        json_dict.get("__type__", None) == "PipxVenvMetadata"
        and "__PipxVenvMetadata__" in json_dict
    ):
        return PipxVenvMetadata(**json_dict["__PipxVenvMetadata__"])
    return json_dict


class Pipxrc:
    def __init__(self, venv_dir: Path, read: bool = True):
        self.venv_dir = venv_dir
        # Reference for Pipx.pipxrc_info, never modify this in runtime
        self.pipxrc_info_template: Dict[str, Any] = {
            "package_or_url": None,
            "install": {
                "pip_args": None,
                "venv_args": None,
                "include_dependencies": None,
            },
            "venv_metadata": None,
            "injected_packages": None,
            "pipxrc_version": "0.1",
        }
        self.pipxrc_info: Dict[str, Any] = {}
        self.reset()
        if read:
            self.read()

    def reset(self):
        self.pipxrc_info = copy.deepcopy(self.pipxrc_info_template)

    def get_package_or_url(self, default: str) -> str:
        if self.pipxrc_info["package_or_url"] is not None:
            return self.pipxrc_info["package_or_url"]
        else:
            return default

    def get_install_pip_args(self, default: List) -> List:
        if self.pipxrc_info["install"]["pip_args"] is not None:
            return self.pipxrc_info["install"]["pip_args"]
        else:
            return default

    def get_install_venv_args(self, default: List) -> List:
        if self.pipxrc_info["install"]["venv_args"] is not None:
            return self.pipxrc_info["install"]["venv_args"]
        else:
            return default

    def get_install_include_dependencies(self, default: bool) -> bool:
        if self.pipxrc_info["install"]["include_dependencies"] is not None:
            return self.pipxrc_info["install"]["include_dependencies"]
        else:
            return default

    def get_venv_metadata(self, default: PipxVenvMetadata) -> PipxVenvMetadata:
        if self.pipxrc_info["venv_metadata"] is not None:
            return self.pipxrc_info["venv_metadata"]
        else:
            return default

    def get_injected_packages(self, default: List) -> List:
        if self.pipxrc_info["injected_packages"] is not None:
            injected_packages = []
            for package in self.pipxrc_info["injected_packages"]:
                package_info = {"package": package}
                package_info.update(self.pipxrc_info["injected_packages"][package])
                injected_packages.append(package_info)
            return injected_packages
        else:
            return default

    def set_package_or_url(self, package_or_url: str):
        # TODO 20190923: if package_or_url is a local path, we need to make it
        #   an absolute path
        self.pipxrc_info["package_or_url"] = package_or_url

    def set_venv_metadata(self, venv_metadata: PipxVenvMetadata):
        self.pipxrc_info["venv_metadata"] = venv_metadata

    def set_install_options(
        self, pip_args: List, venv_args: List, include_dependencies: bool
    ):
        self.pipxrc_info["install"]["pip_args"] = pip_args
        self.pipxrc_info["install"]["venv_args"] = venv_args
        self.pipxrc_info["install"]["include_dependencies"] = include_dependencies

    def add_injected_package(
        self,
        package: str,
        pip_args: List,
        verbose: bool,
        include_apps: bool,
        include_dependencies: bool,
        force: bool,
    ):
        if self.pipxrc_info["injected_packages"] is None:
            self.pipxrc_info["injected_packages"] = {}

        self.pipxrc_info["injected_packages"][package] = {
            "pip_args": pip_args,
            "verbose": verbose,
            "include_apps": include_apps,
            "include_dependencies": include_dependencies,
            "force": force,
        }

    def _get_serializable(self):
        pipxrc_info_ser = copy.deepcopy(self.pipxrc_info)

        # json thinks PipxVenvMetadata is just another tuple, so we override here
        #   (JSONEncoder override is harder and messier.)
        for key in pipxrc_info_ser:
            if isinstance(pipxrc_info_ser[key], PipxVenvMetadata):
                pipxrc_info_ser[key] = {
                    "__type__": "PipxVenvMetadata",
                    "__PipxVenvMetadata__": dict(pipxrc_info_ser[key]._asdict()),
                }
        return pipxrc_info_ser

    def write(self):
        # If writing out, make sure injected_packages is not None, so next
        #   successful read of pipxrc does not use default in
        #   get_injected_packages()
        if self.pipxrc_info["injected_packages"] is None:
            self.pipxrc_info["injected_packages"] = {}

        pipxrc_info_ser = self._get_serializable()
        # TODO 20190919: raise exception on failure?
        with open(self.venv_dir / "pipxrc", "w") as pipxrc_fh:
            json.dump(
                pipxrc_info_ser,
                pipxrc_fh,
                indent=4,
                sort_keys=True,
                cls=JsonEncoderPipx,
            )

    def read(self):
        try:
            with open(self.venv_dir / "pipxrc", "r") as pipxrc_fh:
                self.pipxrc_info = json.load(
                    pipxrc_fh, object_hook=_json_decoder_object_hook
                )
        except IOError:  # Reset self.pipxrc_info if problem reading
            self.reset()
            return
