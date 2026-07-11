from __future__ import annotations

import datetime
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from helpers import (
    run_pipx_cli,
)
from package_info import PKG
from pipx import standalone_python

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest_mock import MockerFixture

MAJOR_PYTHON_VERSION = sys.version_info.major
MINOR_PYTHON_VERSION = sys.version_info.minor
TARGET_PYTHON_VERSION = f"{MAJOR_PYTHON_VERSION}.{MINOR_PYTHON_VERSION}"

original_which = shutil.which


def mock_which(name):
    if name == TARGET_PYTHON_VERSION:
        return None
    return original_which(name)


def test_legacy_standalone_python_index_is_refreshed(pipx_temp_env, monkeypatch):
    legacy_link = (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        "20250818/cpython-3.13.7%2B20250818-x86_64-unknown-linux-gnu-install_only.tar.gz"
    )
    digest = "sha256:" + "0" * 64
    current_releases = [(legacy_link, digest)]
    cache_dir = standalone_python.paths.ctx.standalone_python_cachedir
    index_file = cache_dir / "index.json"
    cache_dir.mkdir(parents=True)
    index_file.write_text(
        json.dumps(
            {
                "fetched": datetime.datetime.now().timestamp(),
                "releases": [legacy_link],
            }
        )
    )

    monkeypatch.setattr(standalone_python, "get_latest_python_releases", lambda: current_releases)

    assert standalone_python.get_or_update_index()["releases"] == current_releases
    assert json.loads(index_file.read_text())["releases"] == [[legacy_link, digest]]


def test_download_standalone_python_sets_tar_filter(
    pipx_temp_env: None,
    mocked_github_api: None,
) -> None:
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        python_path = standalone_python.download_python_build_standalone(TARGET_PYTHON_VERSION)

    assert Path(python_path).is_file()
    assert not [warning for warning in caught_warnings if "filter extracted tar archives" in str(warning.message)]


def test_download_standalone_python_supports_early_python_310(
    pipx_temp_env: None,
    mocked_github_api: None,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    original_extractall = tarfile.TarFile.extractall

    def legacy_extractall(
        archive: tarfile.TarFile,
        path: str | Path = ".",
        members: Iterable[tarfile.TarInfo] | None = None,
        *,
        numeric_owner: bool = False,
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            original_extractall(archive, path, members, numeric_owner=numeric_owner)

    monkeypatch.delattr(tarfile, "data_filter")
    mocker.patch.object(tarfile.TarFile, "extractall", legacy_extractall)

    python_path = standalone_python.download_python_build_standalone(TARGET_PYTHON_VERSION)

    assert Path(python_path).is_file()


def test_download_standalone_python_rejects_unsafe_archive(
    pipx_temp_env: None,
    mocker: MockerFixture,
) -> None:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        for name, content in (("python/bin/python3", b""), ("../outside", b"unsafe")):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            python_tar.addfile(member, io.BytesIO(content))
    archive_bytes = archive.getvalue()
    link = "https://example.invalid/cpython-3.99.0-aarch64-apple-darwin-install_only.tar.gz"
    cache_dir = standalone_python.paths.ctx.standalone_python_cachedir
    cache_dir.mkdir(parents=True)
    (cache_dir / "index.json").write_text(
        json.dumps(
            {
                "fetched": datetime.datetime.now().timestamp(),
                "releases": [[link, f"sha256:{hashlib.sha256(archive_bytes).hexdigest()}"]],
            }
        )
    )
    mocker.patch.object(standalone_python.platform, "system", return_value="Darwin")
    mocker.patch.object(standalone_python.platform, "machine", return_value="arm64")
    mocker.patch.object(standalone_python, "urlopen", return_value=io.BytesIO(archive_bytes))

    with pytest.raises(standalone_python.PipxError, match="Unable to unpack"):
        standalone_python.download_python_build_standalone("3.99")


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
            "--fetch-python=missing",
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
            "--fetch-python=missing",
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
            "--fetch-python=missing",
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
            "--fetch-python=missing",
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


@pytest.mark.parametrize(
    "corrupt_error",
    [
        pytest.param(FileNotFoundError("missing interpreter"), id="missing-executable"),
        pytest.param(subprocess.CalledProcessError(1, ["python", "--version"]), id="nonzero-exit"),
    ],
)
def test_upgrade_standalone_interpreter_skips_corrupt(
    pipx_temp_env: None,
    mocker: MockerFixture,
    corrupt_error: OSError | subprocess.CalledProcessError,
) -> None:
    for name in ("corrupt", "valid"):
        (standalone_python.paths.ctx.standalone_python_cachedir / name).mkdir(parents=True)

    def read_version(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "corrupt" in command[0]:
            raise corrupt_error
        return subprocess.CompletedProcess(command, 0, stdout="Python 3.12.0\n")

    mocker.patch.object(standalone_python, "list_pythons", return_value=["not-a-version", "3.12.1"])
    mocker.patch("pipx.commands.interpreter.subprocess.run", side_effect=read_version)
    download = mocker.patch.object(standalone_python, "download_python_build_standalone")

    assert not run_pipx_cli(["interpreter", "upgrade"])
    download.assert_called_once_with("3.12", override=True)
