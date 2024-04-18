from pathlib import Path

from helpers import run_pipx_cli


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
