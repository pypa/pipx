from pathlib import Path

from helpers import run_pipx_cli
from pipx import paths


def test_install_all(pipx_temp_env, tmp_path, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "black"])
    _ = capsys.readouterr()

    assert not run_pipx_cli(["list", "--json"])
    captured = capsys.readouterr()

    pipx_list_path = Path(tmp_path) / "pipx_list.json"
    with open(pipx_list_path, "w") as pipx_list_fh:
        pipx_list_fh.write(captured.out)

    assert not run_pipx_cli(["install-all", str(pipx_list_path)])

    captured = capsys.readouterr()
    assert "black" in captured.out
    assert "pycowsay" in captured.out


def test_install_all_multiple_errors(pipx_temp_env, root, capsys):
    pipx_metadata_path = root / "testdata" / "pipx_metadata_multiple_errors.json"
    assert run_pipx_cli(["install-all", str(pipx_metadata_path)])
    captured = capsys.readouterr()
    assert "The following package(s) failed to install: dotenv, weblate" in captured.err
    assert f"No packages installed after running 'pipx install-all {pipx_metadata_path}'" in captured.out
    if paths.ctx.log_file:
        with open(paths.ctx.log_file.parent / (paths.ctx.log_file.stem + "_pip_errors.log")) as log_fh:
            log_contents = log_fh.read()
            assert "dotenv" in log_contents
            assert "weblate" in log_contents
