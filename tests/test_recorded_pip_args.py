from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import skip_if_windows
from pipx.package_specifier import recordable_pip_args, replayable_pip_args

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

ONE_SHOT_OPTIONS: Final[list[str]] = [
    "-r",
    "--requirement",
    "--requirements-from-script",
    "-t",
    "--target",
    "--root",
    "--prefix",
    "--src",
    "--source",
    "--source-dir",
    "--source-directory",
    "--report",
    "--log",
    "--log-file",
    "--local-log",
    "--cache-dir",
]


@pytest.fixture
def shared_dir(tmp_path: Path) -> Path:
    shared: Final[Path] = tmp_path.resolve() / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    return shared


@pytest.fixture
def sticky_dir(tmp_path: Path) -> Path:
    sticky: Final[Path] = tmp_path.resolve() / "sticky"
    sticky.mkdir()
    sticky.chmod(0o1777)
    return sticky


@pytest.mark.parametrize("option", ONE_SHOT_OPTIONS)
def test_recordable_pip_args_drops_one_shot_option_separated(option: str) -> None:
    assert recordable_pip_args(["--pre", option, "value", "--no-compile"]) == ["--pre", "--no-compile"]


@pytest.mark.parametrize("option", ONE_SHOT_OPTIONS)
def test_recordable_pip_args_drops_one_shot_option_equals(option: str) -> None:
    assert recordable_pip_args([f"{option}=value", "--no-compile"]) == ["--no-compile"]


@pytest.mark.parametrize("option", ["-r", "-t"])
def test_recordable_pip_args_drops_one_shot_option_attached(option: str) -> None:
    assert recordable_pip_args([f"{option}value", "--no-compile"]) == ["--no-compile"]


def test_recordable_pip_args_drops_trailing_one_shot_option() -> None:
    assert recordable_pip_args(["--no-compile", "--log"]) == ["--no-compile"]


@pytest.mark.parametrize(
    "kept",
    [
        pytest.param(["-c", "constraints.txt"], id="constraint"),
        pytest.param(["--build-constraint=constraints.txt"], id="build-constraint"),
        pytest.param(["-fwheels"], id="find-links-attached"),
        pytest.param(["--find-links", "wheels"], id="find-links"),
        pytest.param(["--cert", "ca.pem"], id="cert"),
        pytest.param(["--client-cert=client.pem"], id="client-cert"),
        pytest.param(["--index-url", "https://index.example/simple"], id="index-url"),
    ],
)
def test_recordable_pip_args_keeps_replayable_option(kept: list[str]) -> None:
    assert recordable_pip_args(kept) == kept


def test_replayable_pip_args_drops_one_shot_option(tmp_path: Path) -> None:
    assert replayable_pip_args(["-r", "requirements.txt", "--no-compile"], tmp_path) == ["--no-compile"]


def test_replayable_pip_args_resolves_relative_path_against_venv(tmp_path: Path) -> None:
    assert replayable_pip_args(["--cert", "ca.pem"], tmp_path) == ["--cert", str((tmp_path / "ca.pem").resolve())]


@pytest.mark.parametrize(
    "kept",
    [
        pytest.param(["--find-links", "https://wheels.example/"], id="url"),
        pytest.param(["--find-links"], id="missing-value"),
    ],
)
def test_replayable_pip_args_keeps_value_without_local_path(tmp_path: Path, kept: list[str]) -> None:
    assert replayable_pip_args(kept, tmp_path) == kept


@skip_if_windows
@pytest.mark.parametrize(
    "option",
    [
        pytest.param("--find-links", id="separated"),
        pytest.param("--find-links=", id="equals"),
        pytest.param("-f", id="attached"),
    ],
)
def test_replayable_pip_args_drops_path_in_world_writable_dir(shared_dir: Path, option: str) -> None:
    wheels: Final[str] = str(shared_dir / "wheels")
    pip_args: Final[list[str]] = [option, wheels] if option == "--find-links" else [f"{option}{wheels}"]

    assert replayable_pip_args([*pip_args, "--no-compile"], shared_dir) == ["--no-compile"]


@skip_if_windows
def test_replayable_pip_args_warns_on_dropped_path(shared_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    replayable_pip_args(["--cert", str(shared_dir / "ca.pem")], shared_dir)

    assert f"ignoring recorded --cert {shared_dir / 'ca.pem'}; another account can change {shared_dir}." in caplog.text


@skip_if_windows
def test_replayable_pip_args_drops_file_url_in_world_writable_dir(shared_dir: Path) -> None:
    assert replayable_pip_args(["-f", (shared_dir / "wheels").as_uri()], shared_dir) == []


@skip_if_windows
def test_replayable_pip_args_drops_missing_path_in_sticky_dir(sticky_dir: Path) -> None:
    assert replayable_pip_args(["-c", str(sticky_dir / "constraints.txt")], sticky_dir) == []


@skip_if_windows
def test_replayable_pip_args_drops_world_writable_find_links_dir(sticky_dir: Path) -> None:
    assert replayable_pip_args(["--find-links", str(sticky_dir)], sticky_dir) == []


@skip_if_windows
def test_replayable_pip_args_keeps_own_path_in_sticky_dir(sticky_dir: Path) -> None:
    wheels: Final[Path] = sticky_dir / "wheels"
    wheels.mkdir(mode=0o755)

    assert replayable_pip_args(["--find-links", str(wheels)], sticky_dir) == ["--find-links", str(wheels)]


@skip_if_windows
@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="root owns the files it creates")
def test_replayable_pip_args_drops_path_owned_by_another_account(tmp_path: Path, mocker: MockerFixture) -> None:
    ca: Final[Path] = tmp_path.resolve() / "ca.pem"
    ca.write_text("", encoding="utf-8")
    mocker.patch("os.geteuid", return_value=ca.stat().st_uid + 1)

    assert replayable_pip_args(["--cert", str(ca)], tmp_path) == []
