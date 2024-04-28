import json
import shutil
import sys

from helpers import (
    run_pipx_cli,
)
from package_info import PKG
from pipx import standalone_python

MAJOR_PYTHON_VERSION = sys.version_info.major
MINOR_PYTHON_VERSION = sys.version_info.minor
TARGET_PYTHON_VERSION = f"{MAJOR_PYTHON_VERSION}.{MINOR_PYTHON_VERSION}"

original_which = shutil.which


def mock_which(name):
    if name == TARGET_PYTHON_VERSION:
        return None
    return original_which(name)


def test_list_no_standalone_interpreters(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["interpreter", "list"])

    captured = capsys.readouterr()
    assert "Standalone interpreters" in captured.out
    assert len(captured.out.splitlines()) == 1


def test_list_used_standalone_interpreters(pipx_temp_env, monkeypatch, mocked_github_api, capsys):
    monkeypatch.setattr(shutil, "which", mock_which)

    assert not run_pipx_cli(
        [
            "install",
            "--fetch-missing-python",
            "--python",
            TARGET_PYTHON_VERSION,
            PKG["pycowsay"]["spec"],
        ]
    )

    capsys.readouterr()
    assert not run_pipx_cli(["interpreter", "list"])

    captured = capsys.readouterr()
    assert TARGET_PYTHON_VERSION in captured.out
    assert "pycowsay" in captured.out


def test_list_unused_standalone_interpreters(pipx_temp_env, monkeypatch, mocked_github_api, capsys):
    monkeypatch.setattr(shutil, "which", mock_which)

    assert not run_pipx_cli(
        [
            "install",
            "--fetch-missing-python",
            "--python",
            TARGET_PYTHON_VERSION,
            PKG["pycowsay"]["spec"],
        ]
    )

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["interpreter", "list"])

    captured = capsys.readouterr()
    assert TARGET_PYTHON_VERSION in captured.out
    assert "pycowsay" not in captured.out
    assert "Unused" in captured.out


def test_prune_unused_standalone_interpreters(pipx_temp_env, monkeypatch, mocked_github_api, capsys):
    monkeypatch.setattr(shutil, "which", mock_which)

    assert not run_pipx_cli(
        [
            "install",
            "--fetch-missing-python",
            "--python",
            TARGET_PYTHON_VERSION,
            PKG["pycowsay"]["spec"],
        ]
    )

    capsys.readouterr()
    assert not run_pipx_cli(["interpreter", "prune"])
    captured = capsys.readouterr()
    assert "Nothing to remove" in captured.out

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["interpreter", "prune"])
    captured = capsys.readouterr()
    assert "Successfully removed:" in captured.out
    assert f"- Python {TARGET_PYTHON_VERSION}" in captured.out

    assert not run_pipx_cli(["interpreter", "list"])
    captured = capsys.readouterr()
    assert "Standalone interpreters" in captured.out
    assert len(captured.out.splitlines()) == 1

    assert not run_pipx_cli(["interpreter", "prune"])
    captured = capsys.readouterr()
    assert "Nothing to remove" in captured.out


def test_upgrade_standalone_interpreter(pipx_temp_env, root, monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", mock_which)

    with open(root / "testdata" / "standalone_python_index_20240107.json") as f:
        new_index = json.load(f)
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda _: new_index)

    assert not run_pipx_cli(
        [
            "install",
            "--fetch-missing-python",
            "--python",
            TARGET_PYTHON_VERSION,
            PKG["pycowsay"]["spec"],
        ]
    )

    with open(root / "testdata" / "standalone_python_index_20240224.json") as f:
        new_index = json.load(f)
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda _: new_index)

    assert not run_pipx_cli(["interpreter", "upgrade"])


def test_upgrade_standalone_interpreter_nothing_to_upgrade(pipx_temp_env, capsys, mocked_github_api):
    assert not run_pipx_cli(["interpreter", "upgrade"])
    captured = capsys.readouterr()
    assert "Nothing to upgrade" in captured.out
