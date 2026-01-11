from helpers import skip_if_windows
from pipx.commands.common import get_exposed_paths_for_package


@skip_if_windows
def test_get_exposed_paths_ignores_recursive_symlink(tmp_path):
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    loop = local_resource_dir / "recursiveexample"
    loop.symlink_to(loop.name)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert loop not in exposed
