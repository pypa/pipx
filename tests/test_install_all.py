import json
from collections.abc import Callable
from pathlib import Path

import pytest

from helpers import run_pipx_cli
from pipx import paths


def test_install_all(
    pipx_temp_env: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    make_pylock: Callable[[str, str], Path],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--app", "pycowsay", "--lock", str(lock_file), "pycowsay"])
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--json"])
    pipx_list_path = tmp_path / "pipx_list.json"
    pipx_list_path.write_text(capsys.readouterr().out, encoding="utf-8")

    assert not run_pipx_cli(["uninstall-all"])
    assert not run_pipx_cli(["install-all", str(pipx_list_path)])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])

    installed = json.loads(capsys.readouterr().out)["venvs"]
    assert (
        sorted(installed),
        sorted(installed["black"]["metadata"]["injected_packages"]),
        installed["pycowsay"]["metadata"]["main_package"]["expected_apps"],
        installed["pycowsay"]["metadata"]["main_package"]["lock_file"],
    ) == (
        ["black", "pycowsay"],
        ["pycowsay"],
        ["pycowsay"],
        {"__Path__": str(lock_file.resolve()), "__type__": "Path"},
    )


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
