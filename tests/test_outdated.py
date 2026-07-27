from __future__ import annotations

import json
import shutil
import subprocess
from contextlib import nullcontext
from dataclasses import replace
from typing import TYPE_CHECKING, Final, Literal, TypeAlias, cast

import pytest

from helpers import mock_legacy_venv, run_pipx_cli
from pipx import paths
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PipxMetadata

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from pathlib import Path
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture

    from pipx.venv import VenvContainer

_JsonValue: TypeAlias = bool | int | float | str | list["_JsonValue"] | dict[str, "_JsonValue"] | None
_OUTDATED_JSON: Final[str] = (
    '[{"name":"pycowsay","version":"0.0.0.2","latest_version":"1.0","latest_filetype":"wheel"},'
    '{"name":"packaging","version":"20","latest_version":"26","latest_filetype":"wheel"}]'
)
_OUTDATED_PROCESS: Final[subprocess.CompletedProcess[str]] = subprocess.CompletedProcess(
    args=[],
    returncode=0,
    stdout=_OUTDATED_JSON,
    stderr="",
)


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_backend(
    capsys: pytest.CaptureFixture[str],
    backend: str,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--backend", backend])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("pipx found no available upgrades.\n", "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_selected_package(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pylint"])
    capsys.readouterr()
    list_outdated = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr=""),
    )

    assert not run_pipx_cli(["list", "pycowsay", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, list_outdated.call_count) == ("pipx found no available upgrades.\n", "", 1)


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_skips_removed_environment(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    def remove_environment(_: VenvContainer, venv_dir: Path) -> AbstractContextManager[None]:
        shutil.rmtree(venv_dir)
        return nullcontext()

    lock: Final[MagicMock] = mocker.patch(
        "pipx.venv.VenvContainer.venv_lock", autospec=True, side_effect=remove_environment
    )

    assert not run_pipx_cli(["list", "--outdated"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err, lock.call_count) == ("pipx found no index packages to check.\n", "", 1)


@pytest.mark.parametrize(
    ("outdated_environment", "expected"),
    [
        pytest.param(_OUTDATED_PROCESS, "pycowsay: 0.0.0.2 -> 1.0\n", id="outdated"),
        pytest.param(
            subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr=""),
            "pipx found no available upgrades.\n",
            id="current",
        ),
    ],
    indirect=["outdated_environment"],
)
def test_list_outdated_text(
    outdated_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
    expected: str,
) -> None:
    assert not run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, outdated_environment.call_count) == (expected, "", 1)


@pytest.mark.usefixtures("outdated_environment")
def test_list_outdated_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["list", "--outdated", "--output", "json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        _outdated_result(
            packages_checked=1,
            packages=(
                {
                    "environment": "pycowsay",
                    "injected": False,
                    "latest_version": "1.0",
                    "package": "pycowsay",
                    "pinned": False,
                    "version": "0.0.0.2",
                },
            ),
        ),
        "",
    )


def test_list_outdated_reports_pinned(
    outdated_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, outdated_environment.call_count) == (
        "pycowsay [pinned]: 0.0.0.2 -> 1.0\n",
        "",
        1,
    )


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        pytest.param([], "pycowsay: 0.0.0.2 -> 1.0\n", id="main-only"),
        pytest.param(
            ["--include-injected"],
            "black (injected in pycowsay): 23 -> 24\npycowsay: 0.0.0.2 -> 1.0\n",
            id="include-injected",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_filters_injected(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    options: list[str],
    expected: str,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()
    mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                '[{"name":"pycowsay","version":"0.0.0.2","latest_version":"1.0"},'
                '{"name":"black","version":"23","latest_version":"24"}]'
            ),
            stderr="",
        ),
    )

    assert not run_pipx_cli(["list", "--outdated", *options])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (expected, "")


@pytest.mark.parametrize(
    ("outdated_environment", "expected_error"),
    [
        pytest.param(
            subprocess.CompletedProcess(args=["pip", "list"], returncode=1, stdout="", stderr="index unavailable"),
            "Package backend exited with code 1.\nstderr: index unavailable",
            id="exit-code",
        ),
        pytest.param(
            subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="not json", stderr=""),
            "Package backend returned invalid JSON for an outdated query.",
            id="invalid-json",
        ),
        pytest.param(
            subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout='[{"name":"demo"}]', stderr=""),
            "Package backend returned invalid JSON for an outdated query.",
            id="missing-key",
        ),
        pytest.param(
            subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="null", stderr=""),
            "Package backend returned invalid JSON for an outdated query.",
            id="null",
        ),
    ],
    indirect=["outdated_environment"],
)
def test_list_outdated_json_reports_backend_failure(
    outdated_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
    expected_error: str,
) -> None:
    assert run_pipx_cli(["list", "--outdated", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err, outdated_environment.call_count) == (
        _outdated_result(
            packages_checked=1,
            failures=({"environment": "pycowsay", "error": expected_error},),
            status="error",
        ),
        "",
        1,
    )


@pytest.mark.parametrize(
    "outdated_environment",
    [
        pytest.param(
            subprocess.CompletedProcess(args=["pip", "list"], returncode=1, stdout="", stderr="index unavailable"),
            id="exit-code",
        )
    ],
    indirect=True,
)
def test_list_outdated_reports_backend_failure(
    outdated_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, outdated_environment.call_count) == (
        "",
        "pycowsay: Package backend exited with code 1.\nstderr: index unavailable\n",
        1,
    )


def test_list_outdated_json_reports_non_index_skip(
    non_index_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["list", "--outdated", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err, non_index_environment.call_count) == (
        _outdated_result(skipped=({"environment": "pycowsay", "package": "pycowsay", "reason": "non-index"},)),
        "",
        0,
    )


def test_list_outdated_reports_no_index_packages(
    non_index_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, non_index_environment.call_count) == (
        "pipx found no index packages to check.\n",
        "",
        0,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_json_reports_editable_skip(
    capsys: pytest.CaptureFixture[str],
    empty_project: Path,
) -> None:
    assert not run_pipx_cli(["install", "--editable", str(empty_project)])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--outdated", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        _outdated_result(skipped=({"environment": "empty-project", "package": "empty-project", "reason": "editable"},)),
        "",
    )


def test_list_outdated_json_reports_corrupt_package(
    corrupt_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "--outdated", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err, corrupt_environment.call_count) == (
        _outdated_result(
            failures=({"environment": "pycowsay", "error": "Package pycowsay has corrupt pipx metadata."},),
            status="error",
        ),
        "",
        0,
    )


def test_list_outdated_reports_corrupt_package(
    corrupt_environment: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err, corrupt_environment.call_count) == (
        "",
        "pycowsay: Package pycowsay has corrupt pipx metadata.\n",
        0,
    )


@pytest.mark.usefixtures("missing_metadata_environment")
def test_list_outdated_json_reports_missing_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "--outdated", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        _outdated_result(
            failures=({"environment": "pycowsay", "error": "Missing internal pipx metadata."},),
            status="error",
        ),
        "",
    )


@pytest.mark.usefixtures("missing_metadata_environment")
def test_list_outdated_reports_missing_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "--outdated"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "pycowsay: Missing internal pipx metadata.\n")


@pytest.mark.parametrize(
    "option",
    [
        pytest.param("--pinned", id="pinned"),
        pytest.param("--short", id="short"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_outdated_rejects_other_filters(
    capsys: pytest.CaptureFixture[str],
    option: str,
) -> None:
    assert run_pipx_cli(["list", "--outdated", option])
    assert capsys.readouterr().err == "--outdated cannot be combined with --short or --pinned.\n"


def _outdated_result(
    *,
    packages_checked: int = 0,
    packages: tuple[dict[str, _JsonValue], ...] = (),
    skipped: tuple[dict[str, _JsonValue], ...] = (),
    failures: tuple[dict[str, _JsonValue], ...] = (),
    status: Literal["success", "partial", "error"] = "success",
) -> dict[str, _JsonValue]:
    return {
        "command": ["list"],
        "data": {
            "packages_checked": packages_checked,
            "packages": list(packages),
            "skipped": list(skipped),
        },
        "errors": [
            {
                "code": "environment_outdated_check_failed",
                "environment": failure["environment"],
                "message": failure["error"],
                "package": None,
            }
            for failure in failures
        ],
        "exit_code": 1 if failures else 0,
        "pipx_result_version": "1",
        "status": status,
    }


@pytest.fixture
def corrupt_environment(outdated_environment: MagicMock) -> MagicMock:
    metadata_path = paths.ctx.venvs / "pycowsay" / PIPX_INFO_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["main_package"]["package_or_url"] = None
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return outdated_environment


@pytest.fixture
def outdated_environment(
    request: pytest.FixtureRequest,
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the environment is built
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> MagicMock:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    process = cast("subprocess.CompletedProcess[str]", getattr(request, "param", _OUTDATED_PROCESS))
    return mocker.patch("pipx.backends.pip.run_subprocess", autospec=True, return_value=process)


@pytest.fixture
def non_index_environment(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the environment is built
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> MagicMock:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    metadata.main_package = replace(metadata.main_package, package_or_url="git+https://example.com/pycowsay.git")
    metadata.write()
    capsys.readouterr()
    return mocker.patch("pipx.backends.pip.run_subprocess", autospec=True)


@pytest.fixture
def missing_metadata_environment(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the environment is built
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    capsys.readouterr()
