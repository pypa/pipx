import os
import subprocess
import sys

from helpers import skip_if_windows
from pipx.commands.common import expose_resources_globally, get_exposed_paths_for_package


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


@skip_if_windows
def test_expose_app_scripts_ignores_pythonpath(tmp_path):
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    shadow_path = tmp_path / "shadow"
    shadow_path.mkdir()

    app_path = venv_resource_path / "demo"
    app_path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"if {str(shadow_path)!r} in sys.path:\n"
        "    raise SystemExit('PYTHONPATH leaked into app script')\n"
        "print('ok')\n"
    )
    app_path.chmod(0o755)

    expose_resources_globally("app", local_resource_dir, [app_path], force=False)

    assert app_path.read_text().splitlines()[0] == f"#!{sys.executable} -E"

    result = subprocess.run(
        [app_path],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(shadow_path)},
        text=True,
    )
    assert result.stdout == "ok\n"
