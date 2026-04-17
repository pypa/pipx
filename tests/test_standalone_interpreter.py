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

    with open(root / "testdata" / "standalone_python_index_20250818.json") as f:
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

    with open(root / "testdata" / "standalone_python_index_20250828.json") as f:
        new_index = json.load(f)
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda _: new_index)

    assert not run_pipx_cli(["interpreter", "upgrade"])


def test_upgrade_standalone_interpreter_nothing_to_upgrade(pipx_temp_env, capsys, mocked_github_api):
    assert not run_pipx_cli(["interpreter", "upgrade"])
    captured = capsys.readouterr()
    assert "Nothing to upgrade" in captured.out


def test_get_latest_python_releases_extracts_hash_only(monkeypatch):
    """Test that get_latest_python_releases extracts just the hash from sha256:prefix format."""
    import urllib.request
    from unittest.mock import Mock

    mock_response = Mock()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    mock_response.read.return_value = json.dumps({
        "assets": [
            {
                "browser_download_url": "https://example.com/cpython-3.12.0-linux-x86_64-gnu.tar.zst",
                "digest": "sha256:a1b2c3d4e5f6abc1234567890abcdef1234567890abcdef1234567890abcdef1234"
            },
            {
                "browser_download_url": "https://example.com/cpython-3.11.0-linux-x86_64-gnu.tar.zst",
                "digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
            }
        ]
    }).encode()

    def mock_urlopen(url):
        return mock_response

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    releases = standalone_python.get_latest_python_releases()

    assert len(releases) == 2
    # Verify that the sha256: prefix is stripped
    assert releases[0][1] == "a1b2c3d4e5f6abc1234567890abcdef1234567890abcdef1234567890abcdef1234"
    assert releases[1][1] == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    # Verify URLs are preserved
    assert releases[0][0] == "https://example.com/cpython-3.12.0-linux-x86_64-gnu.tar.zst"
