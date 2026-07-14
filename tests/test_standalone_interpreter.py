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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from helpers import (
    run_pipx_cli,
)
from package_info import PKG
from pipx import constants, paths, pipx_metadata_file, standalone_python

if TYPE_CHECKING:
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
) -> None:
    # Python 3.10.0-3.10.11 lack tarfile's data filter, so pipx validates members and extracts them by hand
    monkeypatch.delattr(tarfile, "data_filter")

    python_path = standalone_python.download_python_build_standalone(TARGET_PYTHON_VERSION)

    assert Path(python_path).is_file()


@pytest.mark.parametrize(
    "unsafe",
    [
        pytest.param(("../outside", "file"), id="path-traversal"),
        pytest.param(("python/escape", "symlink"), id="escaping-symlink"),
    ],
)
def test_early_python_310_rejects_unsafe_archive(
    pipx_temp_env: None,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    unsafe: tuple[str, str],
) -> None:
    monkeypatch.delattr(tarfile, "data_filter")
    name, kind = unsafe
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        python_tar.addfile(tarfile.TarInfo("python/bin/python3"), io.BytesIO())
        member = tarfile.TarInfo(name)
        if kind == "symlink":
            member.type, member.linkname = tarfile.SYMTYPE, "../../../../etc/passwd"
        python_tar.addfile(member, io.BytesIO())
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

    with pytest.raises(standalone_python.PipxError, match="outside"):
        standalone_python.download_python_build_standalone("3.99")


def test_get_latest_python_releases_sets_request_timeout(mocker: MockerFixture) -> None:
    urlopen = mocker.patch.object(
        standalone_python,
        "urlopen",
        return_value=io.StringIO(json.dumps({"assets": []})),
    )

    assert standalone_python.get_latest_python_releases() == []
    urlopen.assert_called_once_with(standalone_python.GITHUB_API_URL, timeout=30)


def test_download_standalone_python_sets_request_timeout(
    pipx_temp_env: None,
    mocker: MockerFixture,
) -> None:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        for name in ("python/bin/python3", "python/python.exe"):
            python_tar.addfile(tarfile.TarInfo(name), io.BytesIO())
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
    urlopen = mocker.patch.object(standalone_python, "urlopen", return_value=io.BytesIO(archive_bytes))

    python_path = standalone_python.download_python_build_standalone("3.99")

    assert Path(python_path).is_file()
    urlopen.assert_called_once_with(link, timeout=30)


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


def test_list_pythons_windows_arm64(
    mocked_github_api: None,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(standalone_python.platform, "system", return_value="Windows")
    mocker.patch.object(standalone_python.platform, "machine", return_value="ARM64")

    assert standalone_python.list_pythons()["3.13.7"][0].endswith("aarch64-pc-windows-msvc-install_only.tar.gz")


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


@pytest.mark.parametrize("windows", [False, True], ids=["posix", "windows"])
def test_upgrade_standalone_interpreters_reads_each_venv_once(
    pipx_temp_env: None,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    windows: bool,
) -> None:
    monkeypatch.setattr(constants, "WINDOWS", windows)
    for python_version in ("3.11", "3.12"):
        interpreter_dir = paths.ctx.standalone_python_cachedir / python_version
        interpreter_python = interpreter_dir / "python.exe" if windows else interpreter_dir / "bin" / "python3"
        interpreter_python.parent.mkdir(parents=True)
        interpreter_python.touch()

        venv_dir = paths.ctx.venvs / f"demo-{python_version}"
        venv_dir.mkdir(parents=True)
        metadata = pipx_metadata_file.PipxMetadata(venv_dir, read=False)
        metadata.main_package = replace(
            metadata.main_package,
            package=venv_dir.name,
            package_or_url=venv_dir.name,
        )
        metadata.source_interpreter = interpreter_python
        metadata.write()

    def read_version(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        python_path = Path(command[0])
        python_version = python_path.parent.name if windows else python_path.parent.parent.name
        return subprocess.CompletedProcess(command, 0, stdout=f"Python {python_version}.0\n")

    mocker.patch.object(standalone_python, "list_pythons", return_value=["3.11.1", "3.12.1"])
    mocker.patch("pipx.commands.interpreter.subprocess.run", side_effect=read_version)
    download = mocker.patch.object(standalone_python, "download_python_build_standalone")
    reinstall = mocker.patch("pipx.commands.interpreter.commands.reinstall", autospec=True)
    metadata_read = mocker.spy(pipx_metadata_file.PipxMetadata, "read")

    assert not run_pipx_cli(["interpreter", "upgrade"])

    assert download.call_count == 2
    assert reinstall.call_count == 2
    assert metadata_read.call_count == 2


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
