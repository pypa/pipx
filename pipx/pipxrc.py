import json
from pathlib import Path
from typing import Dict, Any

from pipx.Venv import PipxVenvMetadata


# handy, helps enforce some consistency, and adds pipxrc_version
pipxrc_info_template: Dict[str, Any] = {
    "package_or_url": None,
    "install": {"pip_args": [], "venv_args": [], "include_dependencies": None},
    "venv_metadata": None,
    "injected_packages": {},
    "pipxrc_version": 0.1,
}


class JsonEncoderPipx(json.JSONEncoder):
    def default(self, obj):
        # only handles what json.JSONEncoder doesn't understand by default
        if isinstance(obj, Path):
            return {"__type__": "Path", "__Path__": str(obj)}
        return super().default(self, obj)


def _json_decoder_object_hook(json_dict):
    if json_dict.get("__type__", None) == "Path" and "__Path__" in json_dict:
        return Path(json_dict["__Path__"])
    if (
        json_dict.get("__type__", None) == "PipxVenvMetadata"
        and "__PipxVenvMetadata__" in json_dict
    ):
        return PipxVenvMetadata(**json_dict["__PipxVenvMetadata__"])
    return json_dict


def write_pipxrc(venv_dir: Path, pipxrc_info: dict):
    # json thinks PipxVenvMetadata is just another tuple, so we override here
    #   (JSONEncoder override is harder and messier.)
    for key in pipxrc_info:
        if isinstance(pipxrc_info[key], PipxVenvMetadata):
            pipxrc_info[key] = {
                "__type__": "PipxVenvMetadata",
                "__PipxVenvMetadata__": dict(pipxrc_info[key]._asdict()),
            }
    # TODO 20190919: raise exception on failure?
    with open(venv_dir / "pipxrc", "w") as pipxrc_fh:
        json.dump(pipxrc_info, pipxrc_fh, indent=4, sort_keys=True, cls=JsonEncoderPipx)


def read_pipxrc(venv_dir: Path) -> dict:
    try:
        with open(venv_dir / "pipxrc", "r") as pipxrc_fh:
            pipxrc_info = json.load(pipxrc_fh, object_hook=_json_decoder_object_hook)
    except IOError:
        # return empty dict if no pipxrc file or unreadable
        return {}

    return pipxrc_info
