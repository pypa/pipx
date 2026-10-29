from __future__ import annotations

import os
import re
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import skip_if_windows
from pipx.package_specifier import (
    absolute_path_pip_args,
    extract_index_options,
    recordable_pip_args,
    replayable_pip_args,
    trusted_recorded_pip_args,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

ONE_SHOT_OPTIONS: Final[list[str]] = [
    "-r",
    "--requirement",
    "--requirements",
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
    ("pip_args", "expected"),
    [
        pytest.param(["-qr", "/shared/req.txt"], ["-q"], id="clustered-separated"),
        pytest.param(["-qr/shared/req.txt"], ["-q"], id="clustered-attached"),
        pytest.param(["-qr=/shared/req.txt"], ["-q"], id="clustered-equals"),
        pytest.param(["-vvUr", "/shared/req.txt"], ["-vvU"], id="clustered-flags"),
        pytest.param(["-qt/shared/target"], ["-q"], id="clustered-target"),
        pytest.param(["--log-f", "/shared/pip.log"], [], id="abbreviated-log-file"),
        pytest.param(["--loc=/shared/pip.log"], [], id="abbreviated-local-log"),
        pytest.param(["--rep", "/shared/report.json"], [], id="abbreviated-report"),
        pytest.param(["--cache-d", "/shared/cache"], [], id="abbreviated-cache-dir"),
    ],
)
def test_recordable_pip_args_drops_one_shot_spelling(pip_args: list[str], expected: list[str]) -> None:
    assert recordable_pip_args([*pip_args, "--no-compile"]) == [*expected, "--no-compile"]


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
        pytest.param(["--index", "https://index.example/simple"], id="uv-index"),
        pytest.param(["--extra", "dev"], id="uv-extra"),
        pytest.param(["-vv", "--pre"], id="flag-cluster"),
        pytest.param(["--requir", "requirements.txt"], id="ambiguous-prefix"),
        pytest.param(["--no-deps=yes"], id="flag-with-value"),
        pytest.param(["-x"], id="unknown-short"),
    ],
)
def test_recordable_pip_args_keeps_replayable_option(kept: list[str]) -> None:
    assert recordable_pip_args(kept) == kept


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param(["-qf", "/wheels"], ["-q", "-f", "/wheels"], id="clustered-find-links"),
        pytest.param(["-qc/c.txt"], ["-q", "-c/c.txt"], id="clustered-constraint"),
        pytest.param(["-f=/wheels"], ["-f", "/wheels"], id="short-equals"),
        pytest.param(["--find-l", "/wheels"], ["--find-links", "/wheels"], id="abbreviated-find-links"),
        pytest.param(["--find-l=/wheels"], ["--find-links=/wheels"], id="abbreviated-equals"),
        pytest.param(["--constr", "/c.txt"], ["--constraint", "/c.txt"], id="abbreviated-constraint"),
        pytest.param(["--cer", "/ca.pem"], ["--cert", "/ca.pem"], id="abbreviated-cert"),
        pytest.param(["--no-ind"], ["--no-index"], id="abbreviated-flag"),
    ],
)
def test_recordable_pip_args_spells_out_option(pip_args: list[str], expected: list[str]) -> None:
    assert recordable_pip_args(pip_args) == expected


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param(["-qf", "wheels"], ["-q", "-f", "{base}/wheels"], id="clustered"),
        pytest.param(["--find-l=wheels"], ["--find-links={base}/wheels"], id="abbreviated"),
        pytest.param(["-vc", "c.txt"], ["-v", "-c", "{base}/c.txt"], id="clustered-constraint"),
    ],
)
def test_absolute_path_pip_args_resolves_spelling(tmp_path: Path, pip_args: list[str], expected: list[str]) -> None:
    base: Final[Path] = tmp_path.resolve()

    assert absolute_path_pip_args(pip_args, base) == [token.format(base=base) for token in expected]


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param(["-qf", "/wheels", "--pre"], ["-f", "/wheels"], id="clustered-find-links"),
        pytest.param(["--find-l", "/wheels"], ["--find-links", "/wheels"], id="abbreviated-find-links"),
        pytest.param(["--index-u", "https://i.example"], ["--index-url", "https://i.example"], id="abbreviated-index"),
    ],
)
def test_extract_index_options_reads_spelling(pip_args: list[str], expected: list[str]) -> None:
    assert extract_index_options(pip_args) == expected


def test_replayable_pip_args_drops_one_shot_option(tmp_path: Path) -> None:
    assert replayable_pip_args(["-r", "requirements.txt", "--no-compile"], tmp_path) == ["--no-compile"]


def test_replayable_pip_args_drops_clustered_one_shot_option(tmp_path: Path) -> None:
    assert replayable_pip_args(["-qr", "requirements.txt"], tmp_path) == ["-q"]


def test_replayable_pip_args_resolves_relative_path_against_venv(tmp_path: Path) -> None:
    assert replayable_pip_args(["--cert", "ca.pem"], tmp_path) == ["--cert", str((tmp_path / "ca.pem").resolve())]


@skip_if_windows
def test_replayable_pip_args_keeps_path_others_can_change(shared_dir: Path) -> None:
    pip_args: Final[list[str]] = ["--find-links", str(shared_dir / "wheels")]

    assert replayable_pip_args(pip_args, shared_dir) == pip_args


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
    ("pip_args", "spelled"),
    [
        pytest.param(["--find-links", "{shared}/wheels"], "--find-links {shared}/wheels", id="separated"),
        pytest.param(["--find-links={shared}/wheels"], "--find-links={shared}/wheels", id="equals"),
        pytest.param(["-f{shared}/wheels"], "-f{shared}/wheels", id="attached"),
        pytest.param(["-qf", "{shared}/wheels"], "-f {shared}/wheels", id="clustered"),
        pytest.param(["--find-l", "{shared}/wheels"], "--find-links {shared}/wheels", id="abbreviated"),
        pytest.param(["--constr", "{shared}/c.txt"], "--constraint {shared}/c.txt", id="abbreviated-constraint"),
        pytest.param(["--cert", "{shared}/ca.pem"], "--cert {shared}/ca.pem", id="cert"),
        pytest.param(["-b", "{shared}/c.txt"], "-b {shared}/c.txt", id="uv-build-constraints"),
        pytest.param(["-f", "{venv}/wheels,{shared}/wheels"], "-f {venv}/wheels,{shared}/wheels", id="uv-comma"),
    ],
)
def test_trusted_recorded_pip_args_refuses_source_others_can_change(
    shared_dir: Path, tmp_path: Path, pip_args: list[str], spelled: str
) -> None:
    venv: Final[Path] = tmp_path.resolve() / "venv"
    expected: Final[str] = (
        f"venv: refusing to replay the recorded {spelled}: another account can change {{shared}}, and with it what "
        "gets installed. Move the file or directory to a place only you and root can change, or pass the options "
        "again with --pip-args to use them for this run."
    )

    with pytest.raises(PipxError) as error:
        trusted_recorded_pip_args([argument.format(shared=shared_dir, venv=venv) for argument in pip_args], venv)

    assert str(error.value) == expected.format(shared=shared_dir, venv=venv)


@skip_if_windows
@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param(["-f", "{shared_uri}/wheels"], id="find-links-file-url"),
        pytest.param(["--index-url", "{shared_uri}/simple"], id="index-url-file-url"),
        pytest.param(["-i{shared}/simple"], id="index-url-path"),
        pytest.param(["--extra-index-url={shared_uri}/simple"], id="extra-index-url"),
        pytest.param(["--index", "internal={shared_uri}/simple"], id="uv-named-index"),
        pytest.param(["--default-index", "{shared}/simple"], id="uv-default-index"),
        pytest.param(["-i", "simple"], id="relative-index-in-venv"),
    ],
)
def test_trusted_recorded_pip_args_refuses_local_index_others_can_change(shared_dir: Path, pip_args: list[str]) -> None:
    with pytest.raises(PipxError, match=re.escape(f"another account can change {shared_dir},")):
        trusted_recorded_pip_args(
            [argument.format(shared=shared_dir, shared_uri=shared_dir.as_uri()) for argument in pip_args], shared_dir
        )


@skip_if_windows
def test_trusted_recorded_pip_args_refuses_missing_path_in_sticky_dir(sticky_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(PipxError, match=re.escape(f"another account can change {sticky_dir},")):
        trusted_recorded_pip_args(["-c", str(sticky_dir / "constraints.txt")], tmp_path)


@skip_if_windows
def test_trusted_recorded_pip_args_refuses_world_writable_find_links_dir(sticky_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(PipxError, match=re.escape(f"another account can change {sticky_dir},")):
        trusted_recorded_pip_args(["--find-links", str(sticky_dir)], tmp_path)


@skip_if_windows
@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="root owns the files it creates")
def test_trusted_recorded_pip_args_refuses_path_owned_by_another_account(tmp_path: Path, mocker: MockerFixture) -> None:
    ca: Final[Path] = tmp_path.resolve() / "ca.pem"
    ca.write_text("", encoding="utf-8")
    mocker.patch("os.geteuid", return_value=ca.stat().st_uid + 1)

    with pytest.raises(PipxError, match=re.escape(f"another account can change {ca},")):
        trusted_recorded_pip_args(["--cert", str(ca)], tmp_path)


@skip_if_windows
def test_trusted_recorded_pip_args_keeps_own_path_in_sticky_dir(sticky_dir: Path, tmp_path: Path) -> None:
    wheels: Final[Path] = sticky_dir / "wheels"
    wheels.mkdir(mode=0o755)

    assert trusted_recorded_pip_args(["--find-links", str(wheels)], tmp_path) == ["--find-links", str(wheels)]


@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param(["--find-links", "https://wheels.example/"], id="url"),
        pytest.param(["--index-url", "https://index.example/simple"], id="index-url"),
        pytest.param(["--find-links"], id="missing-value"),
        pytest.param(["--log", "{shared}/pip.log"], id="not-a-source"),
    ],
)
def test_trusted_recorded_pip_args_keeps_value_without_shared_source(shared_dir: Path, pip_args: list[str]) -> None:
    recorded: Final[list[str]] = [argument.format(shared=shared_dir) for argument in pip_args]

    assert trusted_recorded_pip_args(recorded, shared_dir.parent) == recorded
