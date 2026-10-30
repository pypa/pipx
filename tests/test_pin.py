from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

import pytest
from packaging.utils import canonicalize_name

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureResult


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert "Not upgrading pinned package pycowsay" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_survives_main_package_extra_injection(local_extras_wheel: Path) -> None:
    assert not run_pipx_cli(["install", str(local_extras_wheel)])
    assert not run_pipx_cli(["pin", "repeatme"])

    assert not run_pipx_cli(["inject", "repeatme", f"{local_extras_wheel}[cow]"])

    assert PipxMetadata(paths.CTX.venvs / "repeatme").main_package.pinned


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--output", "json"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["pin"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "status": "pinned",
                        "version": "0.0.0.2",
                    }
                ],
                "skipped": [],
            },
            "pipx_result_version": "1",
            "errors": [],
            "exit_code": 0,
            "status": "success",
        },
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_json_reports_missing(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "missing", "--output", "json"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["pin"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_pin_failed",
                    "environment": "missing",
                    "message": "pipx does not manage package missing",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        "pipx pinned 1 package in venv pycowsay" in captured.out,
        "pycowsay 0.0.0.2" in captured.out,
    ) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pinned_injected_environment")
def test_pin_json_reports_already_pinned_injected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "pycowsay", "package": "black", "reason": "already-pinned"}],
    }


@pytest.fixture
def pinned_injected_environment(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the environment is built
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])
    capsys.readouterr()


@pytest.mark.usefixtures("pinned_injected_environment")
def test_pin_json_pins_main_after_injected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [
            {
                "environment": "pycowsay",
                "injected": False,
                "location": str(paths.CTX.venvs / "pycowsay"),
                "package": "pycowsay",
                "status": "pinned",
                "version": "0.0.0.2",
            }
        ],
        "skipped": [{"environment": "pycowsay", "package": "black", "reason": "already-pinned"}],
    }


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_json_pins_injected_after_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [
            {
                "environment": "pycowsay",
                "injected": True,
                "location": str(paths.CTX.venvs / "pycowsay"),
                "package": "black",
                "status": "pinned",
                "version": "22.8.0",
            }
        ],
        "skipped": [{"environment": "pycowsay", "package": "pycowsay", "reason": "already-pinned"}],
    }


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_with_suffix(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["upgrade", "black@1"])

    assert "Not upgrading pinned package black@1" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_warning(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "pipx already pins package nox 😴" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_not_installed_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "abc"])

    assert "pipx does not manage package abc" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_only(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["isort"]["spec"]])

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    out: Final[str] = capsys.readouterr().out
    assert not run_pipx_cli(["upgrade", "pycowsay", "--include-injected"])
    assert (
        "pipx pinned 2 packages in venv pycowsay" in out,
        "black" in out,
        "isort" in out,
        "Not upgrading pinned package black in venv pycowsay" in caplog.text,
        "Not upgrading pinned package isort in venv pycowsay" in caplog.text,
    ) == (True, True, True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_only_when_main_package_pinned(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["isort"]["spec"]])

    capsys.readouterr()
    caplog.clear()

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    out: Final[str] = capsys.readouterr().out
    pin_log: Final[str] = caplog.text
    assert not run_pipx_cli(["upgrade", "pycowsay", "--include-injected"])
    assert (
        "pipx pinned 2 packages in venv pycowsay" in out,
        "black" in out,
        "isort" in out,
        "pipx already pins package pycowsay" in pin_log,
        "Not upgrading pinned package pycowsay" in caplog.text,
        "Not upgrading pinned package black in venv pycowsay" in caplog.text,
        "Not upgrading pinned package isort in venv pycowsay" in caplog.text,
    ) == (True, True, True, False, True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_with_skip(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", PKG["pbr"]["spec"], PKG["isort"]["spec"]])

    capsys.readouterr()

    assert not run_pipx_cli(["pin", "black", "--injected-only", "--skip", "isort"])

    out: Final[str] = capsys.readouterr().out
    assert ("pbr" in out, "isort" in out) == (True, False)


_SKIPPED: Final[list[dict[str, str]]] = [
    {"environment": "pycowsay@1", "package": "empty-project", "reason": "requested"}
]


@pytest.mark.parametrize(
    ("suffix", "inject_flags", "skip", "pinned", "reported", "skipped"),
    [
        pytest.param("@1", ["--with-suffix"], "empty-project", False, ["black"], _SKIPPED, id="bare"),
        pytest.param("@1", ["--with-suffix"], "Empty_Project", False, ["black"], _SKIPPED, id="normalized-bare"),
        pytest.param("@1", ["--with-suffix"], "empty-project@1", False, ["black"], _SKIPPED, id="suffixed"),
        pytest.param("@1", ["--with-suffix"], "Empty_Project@1", False, ["black"], _SKIPPED, id="normalized-suffixed"),
        pytest.param(
            "_X",
            ["--with-suffix"],
            "Empty.Project_x",
            False,
            ["black"],
            [{"environment": "pycowsay_X", "package": "empty-project", "reason": "requested"}],
            id="normalized-suffix",
        ),
        pytest.param(
            "@1", ["--with-suffix"], "empty-project@2", True, ["black", "empty-project@1"], [], id="wrong-suffix"
        ),
        pytest.param(
            "@1", ["--with-suffix"], "missing@1", True, ["black", "empty-project@1"], [], id="unknown-package"
        ),
        pytest.param("@1", [], "empty-project", False, ["black"], _SKIPPED, id="unsuffixed-injection"),
        pytest.param("@1", [], "empty-project@1", True, ["black", "empty-project"], [], id="suffix-not-applied"),
        pytest.param(
            "",
            [],
            "Empty_Project",
            False,
            ["black"],
            [{"environment": "pycowsay", "package": "empty-project", "reason": "requested"}],
            id="unsuffixed-environment",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_skip_spelling(
    empty_project_wheel: Path,
    capsys: pytest.CaptureFixture[str],
    suffix: str,
    *,
    inject_flags: list[str],
    skip: str,
    pinned: bool,
    reported: list[str],
    skipped: list[dict[str, str]],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    environment: Final[str] = f"pycowsay{suffix}"
    assert not run_pipx_cli(["inject", environment, str(empty_project_wheel), *inject_flags])
    assert not run_pipx_cli(["inject", environment, PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", environment, "--skip", skip, "--output", "json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / canonicalize_name(environment))
    data: Final = json.loads(capsys.readouterr().out)["data"]
    assert (
        metadata.main_package.pinned,
        {name: package.pinned for name, package in metadata.injected_packages.items()},
        [package["package"] for package in data["packages"]],
        data["skipped"],
    ) == (False, {"empty-project": pinned, "black": True}, reported, skipped)
