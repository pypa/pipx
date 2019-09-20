import json
from pathlib import Path

from pipx.Venv import PipxVenvMetadata


class JsonPathEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            return {'__type__':'Path', '__Path__':str(obj)}
        return super().default(self, obj)


def _json_decoder_object_hook(json_dict):
    if json_dict.get('__type__', None) == 'Path' and '__Path__' in json_dict:
        return Path(json_dict['__Path__'])
    return json_dict


def write_pipxrc(venv_dir: Path, pipxrc_info: dict):
    if 'venv_metadata' in pipxrc_info:
        # serialize PipxVenvMetadata
        pipxrc_info['venv_metadata'] = dict(pipxrc_info['venv_metadata']._asdict())
    # TODO 20190919: raise exception on failure?
    with open(venv_dir / 'pipxrc', 'w') as pipxrc_fh:
        json.dump(pipxrc_info, pipxrc_fh, cls=JsonPathEncoder)


def read_pipxrc(venv_dir: Path) -> dict:
    try:
        with open(venv_dir / 'pipxrc', 'r') as pipxrc_fh:
            pipxrc_info = json.load(pipxrc_fh, object_hook=_json_decoder_object_hook)
    except IOError:
        # return empty dict if no pipxrc file or unreadable
        return {}
    # convert venv_data back to NamedTuple
    if 'venv_metadata' in pipxrc_info:
        pipxrc_info['venv_metadata'] = PipxVenvMetadata(**pipxrc_info['venv_metadata'])

    return pipxrc_info


