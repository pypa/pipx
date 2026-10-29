from __future__ import annotations

import contextlib
import datetime as dt
import email.message
import hashlib
import http.client
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import warnings
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, run_pipx_cli
from package_info import PKG
from pipx import constants, paths, pipx_metadata_file, standalone_python

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

_TARGET_PYTHON_VERSION: Final[str] = f"{sys.version_info.major}.{sys.version_info.minor}"
_DARWIN_LINK: Final[str] = "https://example.invalid/cpython-3.99.0-aarch64-apple-darwin-install_only.tar.gz"


@pytest.mark.usefixtures("pipx_temp_env")
def test_legacy_standalone_python_index_is_refreshed(monkeypatch: pytest.MonkeyPatch) -> None:
    legacy_link: Final[str] = (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        "20250818/cpython-3.13.7%2B20250818-x86_64-unknown-linux-gnu-install_only.tar.gz"
    )
    digest: Final[str] = f"sha256:{'0' * 64}"
    current_releases: Final[list[tuple[str, str]]] = [(legacy_link, digest)]
    (cache_dir := standalone_python.paths.CTX.standalone_python_cachedir).mkdir(parents=True)
    (index_file := cache_dir / "index.json").write_text(
        json.dumps({
            "fetched": dt.datetime.now(tz=dt.UTC).timestamp(),
            "releases": [legacy_link],
        })
    )
    monkeypatch.setattr(standalone_python, "get_latest_python_releases", lambda: current_releases)

    assert (
        standalone_python.get_or_update_index()["releases"],
        json.loads(index_file.read_text())["releases"],
    ) == (current_releases, [[legacy_link, digest]])


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_download_standalone_python_sets_tar_filter() -> None:
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        python_path: Final[str] = standalone_python.download_python_build_standalone(_TARGET_PYTHON_VERSION)

    assert (
        Path(python_path).is_file(),
        [warning for warning in caught_warnings if "filter extracted tar archives" in str(warning.message)],
    ) == (True, [])


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_download_standalone_python_supports_early_python_311(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Python 3.11.0-3.11.3 lack tarfile's data filter, so pipx validates members and extracts them by hand
    monkeypatch.delattr(tarfile, "data_filter")

    python_path: Final[str] = standalone_python.download_python_build_standalone(_TARGET_PYTHON_VERSION)

    assert Path(python_path).is_file()


@pytest.mark.parametrize(
    "unsafe",
    [
        pytest.param(("../outside", tarfile.REGTYPE, ""), id="path-traversal"),
        pytest.param(("python/escape", tarfile.SYMTYPE, "../../../../etc/passwd"), id="escaping-symlink"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_early_python_311_rejects_unsafe_archive(
    monkeypatch: pytest.MonkeyPatch,
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    unsafe: tuple[str, bytes, str],
) -> None:
    monkeypatch.delattr(tarfile, "data_filter")
    archive: Final[io.BytesIO] = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        python_tar.addfile(tarfile.TarInfo("python/bin/python3"), io.BytesIO())
        _add_links(python_tar, [unsafe])
    published_darwin_release[1](archive.getvalue())

    with pytest.raises(standalone_python.PipxError, match="outside"):
        standalone_python.download_python_build_standalone("3.99")


def _add_links(python_tar: tarfile.TarFile, links: Iterable[tuple[str, bytes, str]]) -> None:
    for name, kind, linkname in links:
        member = tarfile.TarInfo(name)
        member.type, member.linkname = kind, linkname
        python_tar.addfile(member)


@pytest.fixture
def published_darwin_release(mocker: MockerFixture) -> tuple[Path, Callable[[bytes], MagicMock]]:
    mocker.patch.object(standalone_python.platform, "system", return_value="Darwin")
    mocker.patch.object(standalone_python.platform, "machine", return_value="arm64")
    (cache_dir := standalone_python.paths.CTX.standalone_python_cachedir).mkdir(parents=True, exist_ok=True)

    def publish(archive_bytes: bytes) -> MagicMock:
        (cache_dir / "index.json").write_text(
            json.dumps({
                "fetched": dt.datetime.now(tz=dt.UTC).timestamp(),
                "releases": [[_DARWIN_LINK, f"sha256:{hashlib.sha256(archive_bytes).hexdigest()}"]],
            })
        )
        return mocker.patch.object(standalone_python, "urlopen", return_value=io.BytesIO(archive_bytes))

    return cache_dir, publish


_DEEP_DIR: Final[str] = f"python/{'/'.join(['d'] * 12)}"
_CLIMB_TO_FILESYSTEM_ROOT: Final[str] = "/".join([".."] * 12)
_SHORTCUTS: Final[str] = "abcdefghijklmnop"
_UNFOLLOWABLE_LINK: Final[str] = f"{'/'.join(_SHORTCUTS)}/{'q' * 254}"


def _links_too_long_to_follow() -> list[tuple[str, bytes, str]]:
    # one-letter links keep the names short enough for the kernel, but resolved they exceed PATH_MAX, so a lenient
    # realpath cannot stat the last two links and takes them for plain directories
    links: Final[list[tuple[str, bytes, str]]] = []
    for depth, shortcut in enumerate(_SHORTCUTS):
        parent = f"{'d' * 247}/" * depth
        links.extend([
            (f"{parent}{'d' * 247}", tarfile.DIRTYPE, ""),
            (f"{parent}{shortcut}", tarfile.SYMTYPE, "d" * 247),
        ])
    return [
        *links,
        (_UNFOLLOWABLE_LINK, tarfile.SYMTYPE, "/".join([".."] * len(_SHORTCUTS))),
        (f"{_UNFOLLOWABLE_LINK}/out", tarfile.SYMTYPE, _CLIMB_TO_FILESYSTEM_ROOT),
    ]


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    ("links", "way_out"),
    [
        pytest.param([], f"{_DEEP_DIR}/up/{_CLIMB_TO_FILESYSTEM_ROOT}", id="name-through-link"),
        pytest.param(
            [("python/out", tarfile.SYMTYPE, f"{'d/' * 12}up/{_CLIMB_TO_FILESYSTEM_ROOT}")],
            "python/out",
            id="link-through-link",
        ),
        pytest.param([("python/out", tarfile.LNKTYPE, f"{_DEEP_DIR}/up")], "python/out", id="hard-link-moves-link"),
        pytest.param(_links_too_long_to_follow(), f"{_UNFOLLOWABLE_LINK}/out", id="links-too-long-to-follow"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_early_python_311_stays_inside_through_archive_links(
    monkeypatch: pytest.MonkeyPatch,
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    tmp_path: Path,
    links: list[tuple[str, bytes, str]],
    way_out: str,
) -> None:
    # the data filter's stand-in must follow the links unpacked before a member
    monkeypatch.delattr(tarfile, "data_filter")
    victim: Final[Path] = tmp_path / "victim"
    archive: Final[io.BytesIO] = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        python_tar.addfile(tarfile.TarInfo("python/bin/python3"), io.BytesIO())
        # on its own this link is fine, it points at the download directory
        _add_links(python_tar, [(f"{_DEEP_DIR}/up", tarfile.SYMTYPE, "/".join([".."] * 13)), *links])
        python_tar.addfile(tarfile.TarInfo(f"{way_out}{victim}"), io.BytesIO())
    published_darwin_release[1](archive.getvalue())

    with contextlib.suppress(standalone_python.PipxError):
        standalone_python.download_python_build_standalone("3.99")

    assert not victim.exists()


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_early_python_311_keeps_links_inside_archive(
    monkeypatch: pytest.MonkeyPatch,
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    tmp_path: Path,
) -> None:
    monkeypatch.delattr(tarfile, "data_filter")
    # from a temp dir on another filesystem, such as a tmpfs /tmp, moving into the pipx home copies the hard link apart
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    archive: Final[io.BytesIO] = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        python_tar.addfile(tarfile.TarInfo("python/bin/python3.99"), io.BytesIO())
        _add_links(
            python_tar,
            [
                ("python/bin/python3", tarfile.SYMTYPE, "python3.99"),
                ("python/bin/python", tarfile.SYMTYPE, "../bin/python3"),
                ("python/lib/python3.99", tarfile.LNKTYPE, "python/bin/python3.99"),
            ],
        )
    published_darwin_release[1](archive.getvalue())

    python_path: Final[Path] = Path(standalone_python.download_python_build_standalone("3.99"))

    assert (
        python_path.is_symlink(),
        python_path.resolve().name,
        (python_path.parent / "python").resolve(),
        (python_path.parents[1] / "lib" / "python3.99").stat().st_nlink,
    ) == (True, "python3.99", python_path.resolve(), 2)


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_upgrade_keeps_old_build_when_unpack_fails(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
) -> None:
    cache_dir, publish = published_darwin_release
    (install_dir := cache_dir / "3.99").joinpath("bin").mkdir(parents=True)
    (install_dir / "bin" / "python3").write_text("old", encoding="utf-8")
    (install_dir / "keepme").write_text("v1", encoding="utf-8")
    publish(b"not a gzip archive")

    with pytest.raises(standalone_python.PipxError, match="Unable to unpack"):
        standalone_python.download_python_build_standalone("3.99", override=True)

    assert ((install_dir / "keepme").read_text(encoding="utf-8"), (install_dir / "bin" / "python3").read_text()) == (
        "v1",
        "old",
    )


def _python_archive_bytes() -> bytes:
    archive: Final[io.BytesIO] = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        for name in ("python/bin/python3", "python/python.exe"):
            python_tar.addfile(tarfile.TarInfo(name), io.BytesIO())
    return archive.getvalue()


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_upgrade_replaces_existing_build(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
) -> None:
    cache_dir, publish = published_darwin_release
    (install_dir := cache_dir / "3.99").mkdir(parents=True)
    (stale := install_dir / "stale").write_text("old", encoding="utf-8")
    publish(_python_archive_bytes())

    python_path: Final[str] = standalone_python.download_python_build_standalone("3.99", override=True)

    assert (Path(python_path).is_file(), stale.exists()) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_upgrade_restores_backup_when_swap_fails(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
) -> None:
    cache_dir, publish = published_darwin_release
    (install_dir := cache_dir / "3.99").joinpath("bin").mkdir(parents=True)
    (install_dir / "keepme").write_text("v1", encoding="utf-8")
    publish(_python_archive_bytes())
    real_replace: Final = Path.replace
    failed: Final[list[bool]] = []

    def replace(self: Path, target: Path) -> Path:
        if target == install_dir and not failed:
            failed.append(True)
            msg = "swap failed"
            raise OSError(msg)
        return real_replace(self, target)

    mocker.patch.object(Path, "replace", autospec=True, side_effect=replace)

    with pytest.raises(OSError, match="swap failed"):
        standalone_python.download_python_build_standalone("3.99", override=True)

    assert (install_dir / "keepme").read_text(encoding="utf-8") == "v1"


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_concurrent_fetch_waits_and_reuses_build(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
) -> None:
    published_darwin_release[1](_python_archive_bytes())
    real_move: Final = shutil.move
    concurrent: Final[list[Future[str]]] = []

    def move_into_staging(source: str, destination: str) -> str:
        # start the second fetch while the first one is moving its build into the staging directory
        if not concurrent:
            concurrent.append(executor.submit(standalone_python.download_python_build_standalone, "3.99"))
            with pytest.raises(TimeoutError):
                concurrent[0].result(timeout=0.2)
        return real_move(source, destination)

    moves: Final = mocker.patch.object(shutil, "move", side_effect=move_into_staging)

    with ThreadPoolExecutor(max_workers=1) as executor:
        python_path: Final[str] = standalone_python.download_python_build_standalone("3.99")

    assert (concurrent[0].result(), moves.call_count, Path(python_path).is_file()) == (python_path, 1, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_download_retries_transient_http_error(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
    http_error: Callable[[int], urllib.error.HTTPError],
) -> None:
    archive_bytes: Final[bytes] = _python_archive_bytes()
    published_darwin_release[1](archive_bytes)
    mocker.patch.object(standalone_python, "urlopen", side_effect=[http_error(503), io.BytesIO(archive_bytes)])
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    python_path: Final[str] = standalone_python.download_python_build_standalone("3.99")

    assert (Path(python_path).is_file(), sleep.call_count) == (True, 1)


@pytest.fixture
def http_error() -> Iterator[Callable[[int], urllib.error.HTTPError]]:
    errors: Final[list[urllib.error.HTTPError]] = []

    def make(code: int) -> urllib.error.HTTPError:
        error = urllib.error.HTTPError("https://example.invalid", code, "boom", email.message.Message(), None)
        errors.append(error)
        return error

    yield make
    # urllib hands a synthetic HTTPError an unclosed body, which warns once the object is collected
    for error in errors:
        error.close()


@pytest.mark.parametrize(
    ("code", "sleeps"),
    [
        pytest.param(404, 0, id="missing-build-not-retried"),
        pytest.param(500, 2, id="server-error-retried-until-giving-up"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_download_fails_on_http_error(  # pytest injects fixtures by name
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
    http_error: Callable[[int], urllib.error.HTTPError],
    code: int,
    sleeps: int,
) -> None:
    published_darwin_release[1](_python_archive_bytes())
    mocker.patch.object(standalone_python, "urlopen", side_effect=http_error(code))
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    with pytest.raises(standalone_python.PipxError, match="Unable to download"):
        standalone_python.download_python_build_standalone("3.99")

    assert sleep.call_count == sleeps


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_download_resumes_after_disconnect(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
) -> None:
    archive_bytes: Final[bytes] = _python_archive_bytes()
    published_darwin_release[1](archive_bytes)
    urlopen: Final[MagicMock] = mocker.patch.object(
        standalone_python,
        "urlopen",
        side_effect=[
            _interrupted_response(mocker, archive_bytes[:10]),
            _range_response(mocker, HTTPStatus.PARTIAL_CONTENT, archive_bytes[10:]),
        ],
    )
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    python_path: Final[str] = standalone_python.download_python_build_standalone("3.99")

    first_request, second_request = (call.args[0] for call in urlopen.call_args_list)
    assert (
        Path(python_path).is_file(),
        sleep.call_count,
        first_request.get_header("Range"),
        second_request.get_header("Range"),
    ) == (True, 1, None, "bytes=10-")


def _interrupted_response(mocker: MockerFixture, chunk: bytes) -> MagicMock:
    return mocker.MagicMock(**{
        "__enter__.return_value.read.side_effect": [chunk, http.client.RemoteDisconnected("closed")]
    })


def _range_response(mocker: MockerFixture, status: HTTPStatus, body: bytes) -> MagicMock:
    return mocker.MagicMock(**{
        "__enter__.return_value.status": status,
        "__enter__.return_value.read.side_effect": [body, b""],
    })


@pytest.mark.usefixtures("pipx_temp_env")
def test_standalone_python_download_restarts_when_range_ignored(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
    mocker: MockerFixture,
) -> None:
    archive_bytes: Final[bytes] = _python_archive_bytes()
    published_darwin_release[1](archive_bytes)
    mocker.patch.object(
        standalone_python,
        "urlopen",
        side_effect=[
            _interrupted_response(mocker, archive_bytes[:10]),
            _range_response(mocker, HTTPStatus.OK, archive_bytes),
        ],
    )
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    python_path: Final[str] = standalone_python.download_python_build_standalone("3.99")

    assert (Path(python_path).is_file(), sleep.call_count) == (True, 1)


def test_get_latest_python_releases_retries_transient_http_error(
    mocker: MockerFixture, http_error: Callable[[int], urllib.error.HTTPError]
) -> None:
    release: Final[dict[str, str]] = {
        "browser_download_url": "https://example.invalid/x.tar.gz",
        "digest": f"sha256:{'0' * 64}",
    }
    mocker.patch.object(
        standalone_python,
        "urlopen",
        side_effect=[http_error(503), io.StringIO(json.dumps({"assets": [release]}))],
    )
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    releases: Final[list[tuple[str, str]]] = standalone_python.get_latest_python_releases()

    assert (releases, sleep.call_count) == ([(release["browser_download_url"], release["digest"])], 1)


@pytest.mark.parametrize(
    ("code", "sleeps"),
    [
        pytest.param(404, 0, id="missing-release-not-retried"),
        pytest.param(500, 2, id="server-error-retried-until-giving-up"),
    ],
)
def test_get_latest_python_releases_fails_on_http_error(
    mocker: MockerFixture, http_error: Callable[[int], urllib.error.HTTPError], code: int, sleeps: int
) -> None:
    mocker.patch.object(standalone_python, "urlopen", side_effect=http_error(code))
    sleep: Final[MagicMock] = mocker.patch.object(standalone_python.time, "sleep")

    with pytest.raises(standalone_python.PipxError, match="Unable to fetch"):
        standalone_python.get_latest_python_releases()

    assert sleep.call_count == sleeps


def test_get_latest_python_releases_sets_request_timeout(mocker: MockerFixture) -> None:
    urlopen: Final[MagicMock] = mocker.patch.object(
        standalone_python,
        "urlopen",
        return_value=io.StringIO(json.dumps({"assets": []})),
    )

    assert standalone_python.get_latest_python_releases() == []
    urlopen.assert_called_once_with(standalone_python.GITHUB_API_URL, timeout=30)


@pytest.mark.usefixtures("pipx_temp_env")
def test_download_standalone_python_sets_request_timeout(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
) -> None:
    urlopen: Final[MagicMock] = published_darwin_release[1](_python_archive_bytes())

    python_path: Final[str] = standalone_python.download_python_build_standalone("3.99")

    (request,), kwargs = urlopen.call_args
    assert (Path(python_path).is_file(), urlopen.call_count, request.full_url, kwargs) == (
        True,
        1,
        _DARWIN_LINK,
        {"timeout": 30},
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_download_standalone_python_rejects_unsafe_archive(
    published_darwin_release: tuple[Path, Callable[[bytes], MagicMock]],
) -> None:
    archive: Final[io.BytesIO] = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as python_tar:
        for name, content in (("python/bin/python3", b""), ("../outside", b"unsafe")):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            python_tar.addfile(member, io.BytesIO(content))
    published_darwin_release[1](archive.getvalue())

    with pytest.raises(standalone_python.PipxError, match="Unable to unpack"):
        standalone_python.download_python_build_standalone("3.99")


@pytest.mark.usefixtures("mocked_github_api")
def test_list_pythons_windows_arm64(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(standalone_python.platform, "system", return_value="Windows")
    mocker.patch.object(standalone_python.platform, "machine", return_value="ARM64")

    full_version: Final[str] = "{}.{}.{}".format(*sys.version_info[:3])
    assert standalone_python.list_pythons()[full_version][0].endswith("aarch64-pc-windows-msvc-install_only.tar.gz")


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_no_standalone_interpreters(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "list"])

    out: Final[str] = capsys.readouterr().out
    assert ("Standalone interpreters" in out, len(out.splitlines())) == (True, 1)


@pytest.mark.usefixtures("pycowsay_on_fetched_python")
def test_list_used_standalone_interpreters(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "list"])

    out: Final[str] = capsys.readouterr().out
    assert (_TARGET_PYTHON_VERSION in out, "pycowsay" in out) == (True, True)


@pytest.fixture
def pycowsay_on_fetched_python(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    mocked_github_api: None,  # ruff:ignore[unused-function-argument]  # the fetched build comes from the canned index
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    which: Final = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name: None if name == _TARGET_PYTHON_VERSION else which(name))
    assert not run_pipx_cli([
        "install",
        "--fetch-python=missing",
        "--python",
        _TARGET_PYTHON_VERSION,
        PKG["pycowsay"]["spec"],
    ])
    capsys.readouterr()


@pytest.mark.usefixtures("pycowsay_on_fetched_python")
def test_list_unused_standalone_interpreters(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["interpreter", "list"])

    out: Final[str] = capsys.readouterr().out
    assert (_TARGET_PYTHON_VERSION in out, "pycowsay" in out, "Unused" in out) == (True, False, True)


@pytest.mark.usefixtures("pycowsay_on_fetched_python")
def test_prune_keeps_used_standalone_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "prune"])

    assert "Nothing to remove" in capsys.readouterr().out


@pytest.mark.usefixtures("pycowsay_on_fetched_python")
def test_prune_removes_unused_standalone_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["interpreter", "prune"])

    out: Final[str] = capsys.readouterr().out
    assert ("Successfully removed:" in out, f"- Python {_TARGET_PYTHON_VERSION}" in out) == (True, True)


@pytest.mark.usefixtures("pruned_unused_interpreter")
def test_list_after_prune_shows_no_standalone_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "list"])

    out: Final[str] = capsys.readouterr().out
    assert ("Standalone interpreters" in out, len(out.splitlines())) == (True, 1)


@pytest.fixture
def pruned_unused_interpreter(
    pycowsay_on_fetched_python: None,  # ruff:ignore[unused-function-argument]  # prune needs an interpreter to remove
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not run_pipx_cli(["interpreter", "prune"])
    capsys.readouterr()


@pytest.mark.usefixtures("pruned_unused_interpreter")
def test_prune_after_prune_has_nothing_to_remove(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "prune"])

    assert "Nothing to remove" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_prune_keeps_standalone_interpreter_being_fetched(capsys: pytest.CaptureFixture[str]) -> None:
    (staging_dir := paths.CTX.standalone_python_cachedir / ".3.99.incoming").mkdir(parents=True)

    assert not run_pipx_cli(["interpreter", "prune"])

    assert ("Nothing to remove" in capsys.readouterr().out, staging_dir.is_dir()) == (True, True)


@pytest.mark.usefixtures("pycowsay_on_fetched_python")
def test_upgrade_standalone_interpreter(
    monkeypatch: pytest.MonkeyPatch,
    standalone_python_index: Callable[[str], dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    newer_index: Final[dict[str, object]] = standalone_python_index(
        f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2] + 1}"
    )
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda **_: newer_index)

    assert not run_pipx_cli(["interpreter", "upgrade"])

    out: Final[str] = capsys.readouterr().out
    assert ("Successfully upgraded the interpreter(s):" in out, "pycowsay" in out) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_upgrade_patch_pinned_standalone_interpreter_moves_venv_to_new_build(
    monkeypatch: pytest.MonkeyPatch,
    standalone_python_index: Callable[[str], dict[str, object]],
) -> None:
    assert not run_pipx_cli([
        "install",
        "--fetch-python=always",
        "--python",
        "{}.{}.{}".format(*sys.version_info[:3]),
        PKG["pycowsay"]["spec"],
    ])
    newer_index: Final[dict[str, object]] = standalone_python_index(
        f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2] + 1}"
    )
    monkeypatch.setattr(standalone_python, "get_or_update_index", lambda **_: newer_index)

    assert not run_pipx_cli(["interpreter", "upgrade"])

    interpreter_dir: Final[Path] = paths.CTX.standalone_python_cachedir / _TARGET_PYTHON_VERSION
    expected: Final[Path] = interpreter_dir / "python.exe" if constants.WINDOWS else interpreter_dir / "bin" / "python3"
    assert pipx_metadata_file.PipxMetadata(paths.CTX.venvs / "pycowsay").source_interpreter == expected


@pytest.mark.parametrize("windows", [False, True], ids=["posix", "windows"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_standalone_interpreters_reads_each_venv_once(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    windows: bool,
) -> None:
    monkeypatch.setattr(constants, "WINDOWS", windows)
    for python_version in ("3.11", "3.12"):
        interpreter_dir = paths.CTX.standalone_python_cachedir / python_version
        interpreter_python = interpreter_dir / "python.exe" if windows else interpreter_dir / "bin" / "python3"
        interpreter_python.parent.mkdir(parents=True)
        interpreter_python.touch()

        (venv_dir := paths.CTX.venvs / f"demo-{python_version}").mkdir(parents=True)
        metadata = pipx_metadata_file.PipxMetadata(venv_dir, read=False)
        metadata.main_package = replace(
            metadata.main_package,
            package=venv_dir.name,
            package_or_url=venv_dir.name,
        )
        metadata.source_interpreter = interpreter_python
        metadata.write()

    def read_version(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        python_path = Path(command[0])
        python_version = python_path.parent.name if windows else python_path.parent.parent.name
        return subprocess.CompletedProcess(command, 0, stdout=f"Python {python_version}.0\n")

    mocker.patch.object(standalone_python, "list_pythons", return_value=["3.11.1", "3.12.1"])
    mocker.patch("pipx.commands.interpreter.subprocess.run", side_effect=read_version)
    download: Final[MagicMock] = mocker.patch.object(standalone_python, "download_python_build_standalone")
    reinstall: Final[MagicMock] = mocker.patch("pipx.commands.interpreter.reinstall", autospec=True)
    metadata_read: Final[MagicMock] = mocker.spy(pipx_metadata_file.PipxMetadata, "read")

    assert not run_pipx_cli(["interpreter", "upgrade"])

    assert (download.call_count, reinstall.call_count, metadata_read.call_count) == (2, 2, 2)


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_upgrade_standalone_interpreter_nothing_to_upgrade(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["interpreter", "upgrade"])

    assert "Nothing to upgrade" in capsys.readouterr().out


@pytest.mark.parametrize(
    "corrupt_error",
    [
        pytest.param(FileNotFoundError("missing interpreter"), id="missing-executable"),
        pytest.param(subprocess.CalledProcessError(1, ["python", "--version"]), id="nonzero-exit"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_standalone_interpreter_skips_corrupt(
    mocker: MockerFixture,
    corrupt_error: OSError | subprocess.CalledProcessError,
) -> None:
    for name in ("corrupt", "valid"):
        (standalone_python.paths.CTX.standalone_python_cachedir / name).mkdir(parents=True)

    def read_version(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "corrupt" in command[0]:
            raise corrupt_error
        return subprocess.CompletedProcess(command, 0, stdout="Python 3.12.0\n")

    mocker.patch.object(standalone_python, "list_pythons", return_value=["not-a-version", "3.12.1"])
    mocker.patch("pipx.commands.interpreter.subprocess.run", side_effect=read_version)
    download: Final[MagicMock] = mocker.patch.object(standalone_python, "download_python_build_standalone")

    assert not run_pipx_cli(["interpreter", "upgrade"])
    download.assert_called_once_with("3.12", override=True)
