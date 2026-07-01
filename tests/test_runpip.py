import json
import subprocess
import sys

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths


def test_runpip(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list"])


def test_runpip_splits_single_argument(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list --format=freeze"])


@skip_if_windows
def test_runpip_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["runpip", "--global", "pycowsay", "list"])


def test_runpip_install_refreshes_main_package_metadata(pipx_temp_env, root, tmp_path):
    package_dir = root / "testdata" / "empty_project"
    wheel_dir = tmp_path / "wheelhouse"
    wheel_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(package_dir), "--no-deps", "--wheel-dir", str(wheel_dir)],
        check=True,
    )
    wheel_path = next(wheel_dir.glob("empty_project-*.whl"))

    assert not run_pipx_cli(["install", "--editable", str(package_dir)])

    metadata_path = paths.ctx.venvs / "empty-project" / "pipx_metadata.json"
    before = json.loads(metadata_path.read_text())
    assert before["main_package"]["package_or_url"] == str(package_dir.resolve())
    assert before["main_package"]["pip_args"] == ["--editable"]

    assert not run_pipx_cli(["runpip", "empty-project", "install", "--force-reinstall", str(wheel_path)])

    after = json.loads(metadata_path.read_text())
    assert after["main_package"]["package_or_url"] == str(wheel_path.resolve())
    assert after["main_package"]["pip_args"] == []
