import json
from collections.abc import Callable
from pathlib import Path

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli
from pipx import paths


def test_upgrade_all(pipx_temp_env, capsys):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])


def test_upgrade_all_none(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])
    captured = capsys.readouterr()
    assert "No packages upgraded after running 'pipx upgrade-all'" in captured.out


def test_upgrade_all_quiet(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--quiet"])

    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_upgrade_all_json(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--json"])

    captured = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": "upgrade-all",
        "data": {
            "failures": [],
            "packages": [
                {
                    "environment": "pycowsay",
                    "injected": False,
                    "location": str(paths.ctx.venvs / "pycowsay"),
                    "package": "pycowsay",
                    "previous_version": "0.0.0.2",
                    "status": "unchanged",
                    "version": "0.0.0.2",
                }
            ],
            "skipped": [],
        },
        "pipx_result_version": "0.1",
        "status": "success",
    }


def test_upgrade_all_pylock_json(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--json"])

    assert json.loads(capsys.readouterr().out)["data"]["packages"] == [
        {
            "environment": "pycowsay",
            "injected": False,
            "location": str(paths.ctx.venvs / "pycowsay"),
            "package": "pycowsay",
            "previous_version": "0.0.0.2",
            "status": "locked",
            "version": "0.0.0.2",
        }
    ]


def test_upgrade_all_json_failure(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["upgrade-all", "--json"])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert not captured.err
    assert result["status"] == "error"
    assert result["data"]["packages"] == []
    assert result["data"]["skipped"] == []
    assert result["data"]["failures"][0]["environment"] == "pycowsay"
    assert "missing internal pipx metadata" in result["data"]["failures"][0]["error"]


def test_upgrade_all_json_requested_skip(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--skip", "pycowsay", "--json"])

    result = json.loads(capsys.readouterr().out)
    assert result["data"]["packages"] == []
    assert result["data"]["skipped"] == [{"environment": "pycowsay", "reason": "requested"}]


def test_upgrade_all_json_editable_skip(pipx_temp_env: None, capsys: pytest.CaptureFixture[str], root: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", str(root / "testdata" / "empty_project"), "--force"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--json"])

    result = json.loads(capsys.readouterr().out)
    assert result["data"]["packages"] == []
    assert result["data"]["skipped"] == [{"environment": "empty-project", "reason": "editable"}]


def test_upgrade_all_with_pip_args(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all", "--pip-args=--no-cache-dir"])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_upgrade_all_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is None:
        capsys.readouterr()
        assert run_pipx_cli(["upgrade-all"])
        assert "The following package(s) failed to upgrade: pycowsay" in capsys.readouterr().err
    else:
        assert not run_pipx_cli(["upgrade-all"])
