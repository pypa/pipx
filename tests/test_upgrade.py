from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from typing import TYPE_CHECKING, Final

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    SKIP_IF_WINDOWS,
    app_name,
    drop_extra_app,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    unwrap_log_text,
    write_wheel,
)
from package_info import PKG
from pipx import paths, shared_libs
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, PipxMetadata
from pipx.redact import redact_url_credentials

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "scope", [pytest.param([], id="user"), pytest.param(["--global"], id="global", marks=SKIP_IF_WINDOWS)]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_not_installed_fails(capsys: pytest.CaptureFixture[str], scope: list[str]) -> None:
    assert run_pipx_cli(["upgrade", *scope, "pycowsay"])

    assert "Package is not installed" in capsys.readouterr().err


@pytest.mark.parametrize(
    "scope", [pytest.param([], id="user"), pytest.param(["--global"], id="global", marks=SKIP_IF_WINDOWS)]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_reports_latest_version(capsys: pytest.CaptureFixture[str], scope: list[str]) -> None:
    assert not run_pipx_cli(["install", *scope, "pycowsay"])
    assert "installed package pycowsay" in capsys.readouterr().out

    assert not run_pipx_cli(["upgrade", *scope, "pycowsay"])

    assert "pycowsay is already at latest version" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize("flags", [pytest.param([], id="plain"), pytest.param(["--verbose"], id="verbose")])
def test_upgrade_failure_prints_installer_error_once(capsys: pytest.CaptureFixture[str], flags: list[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", *flags, "--pip-args=--no-such-flag", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out + captured.err).count("no such option: --no-such-flag") == 1


@pytest.mark.parametrize(
    ("age_sec", "disable_auto_upgrade", "upgrade_args", "refreshed"),
    [
        pytest.param(dt.timedelta(days=1).total_seconds(), "0", [], False, id="recent"),
        pytest.param(shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60, "0", [], True, id="stale"),
        pytest.param(shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60, "1", [], False, id="stale-auto-upgrade-disabled"),
        pytest.param(
            shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60, "0", ["--skip-maintenance"], False, id="stale-skip-maintenance"
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_refreshes_shared_pip_only_when_due(  # ruff:ignore[too-many-positional-arguments]  # pytest injects fixtures by name
    monkeypatch: pytest.MonkeyPatch,
    age_shared_pip: Callable[[float], float],
    age_sec: float,
    disable_auto_upgrade: str,
    upgrade_args: list[str],
    refreshed: bool,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, disable_auto_upgrade)
    last_upgrade: Final[float] = age_shared_pip(age_sec)

    assert not run_pipx_cli(["upgrade", "pycowsay", *upgrade_args])

    assert (shared_libs.SHARED_LIBS.pip_path.stat().st_mtime != last_upgrade) is refreshed


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_records_relative_find_links_as_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["upgrade", "pycowsay", "--pip-args=--find-links wheels"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == [
        "--find-links",
        str((tmp_path / "wheels").resolve()),
    ]


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_resolves_recorded_relative_find_links_in_venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(metadata.main_package, pip_args=["--find-links", "wheels"])
    metadata.write()
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert PipxMetadata(venv_dir).main_package.pip_args == ["--find-links", str((venv_dir / "wheels").resolve())]


@SKIP_IF_WINDOWS
@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="root owns the files it creates")
def test_upgrade_refuses_recorded_find_links_owned_by_another_account(
    recorded_find_links: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch("os.geteuid", return_value=recorded_find_links.stat().st_uid + 1)
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert (
        f"pycowsay: refusing to replay the recorded --find-links {recorded_find_links}: another account can change "
        f"{recorded_find_links}, and with it what gets installed."
    ) in capsys.readouterr().err


@pytest.fixture
def recorded_find_links(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
) -> Path:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    (wheels := tmp_path.resolve() / "wheels").mkdir()
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    metadata.main_package = replace(metadata.main_package, pip_args=["--find-links", str(wheels)])
    metadata.write()
    return wheels


@SKIP_IF_WINDOWS
@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="root owns the files it creates")
def test_upgrade_keeps_metadata_of_refused_find_links(recorded_find_links: Path, mocker: MockerFixture) -> None:
    metadata_file: Final[Path] = paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME
    recorded: Final[bytes] = metadata_file.read_bytes()
    mocker.patch("os.geteuid", return_value=recorded_find_links.stat().st_uid + 1)

    run_pipx_cli(["upgrade", "pycowsay"])

    assert metadata_file.read_bytes() == recorded


def test_upgrade_replays_recorded_find_links_owned_by_user(recorded_find_links: Path) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == [
        "--find-links",
        str(recorded_find_links),
    ]


@SKIP_IF_WINDOWS
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_upgrade_refuses_recorded_uv_project_writable_by_others(
    recorded_uv_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recorded_uv_project.chmod(0o777)
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert (
        f"pycowsay: refusing to replay the recorded --project {recorded_uv_project}: another account can change "
        f"{recorded_uv_project}, and with it what gets installed."
    ) in capsys.readouterr().err


@pytest.fixture
def recorded_uv_project(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
) -> Path:
    assert not run_pipx_cli(["install", "--backend", "uv", "pycowsay"])
    (project := tmp_path.resolve() / "project").mkdir()
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    metadata.main_package = replace(metadata.main_package, pip_args=["--project", str(project)])
    metadata.write()
    return project


@SKIP_IF_WINDOWS
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_upgrade_keeps_metadata_of_refused_uv_project(recorded_uv_project: Path) -> None:
    metadata_file: Final[Path] = paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME
    recorded: Final[bytes] = metadata_file.read_bytes()
    recorded_uv_project.chmod(0o777)

    run_pipx_cli(["upgrade", "pycowsay"])

    assert metadata_file.read_bytes() == recorded


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_upgrade_replays_recorded_uv_project_owned_by_user(recorded_uv_project: Path) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == ["--project", str(recorded_uv_project)]


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_refuses_recorded_file_index_url_writable_by_others(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    (shared := tmp_path.resolve() / "shared").mkdir()
    shared.chmod(0o777)
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    metadata.main_package = replace(metadata.main_package, pip_args=["--index-url", (shared / "simple").as_uri()])
    metadata.write()
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert f"another account can change {shared}, and with it what gets installed." in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_inline_script(inline_script: Path) -> None:
    assert not run_pipx_cli(["install", "--app", "greet", str(inline_script)])
    inline_script.write_text(
        inline_script.read_text(encoding="utf-8").replace("installed", "upgraded"),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["upgrade", "greet"])

    assert (
        subprocess.run([paths.CTX.bin_dir / app_name("greet")], check=True, capture_output=True, text=True).stdout
        == "upgraded\n"
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_unchanged_inline_script_offers_no_index_reinstall(
    inline_script: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", str(inline_script)])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", "hello"])

    upgrade_out: Final[str] = " ".join(capsys.readouterr().out.split())
    assert ("installed from the local source" in upgrade_out, "pipx install --force" in upgrade_out) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", "pycowsay", "--output", "json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["upgrade"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "previous_version": "0.0.0.2",
                        "status": "unchanged",
                        "version": "0.0.0.2",
                        "interpreter": metadata.python_version,
                        "backend": metadata.backend,
                        "source": None,
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


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["upgrade", "pycowsay"], id="one"),
        pytest.param(["upgrade-all"], id="all"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_skips_pylock(
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    command: list[str],
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(command)

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (
        "Not upgrading locked package pycowsay. Update its lock file and run `pipx reinstall pycowsay`."
        in unwrap_log_text(capsys.readouterr().out),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_legacy_venv_without_metadata_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=None)
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert "Not upgrading pycowsay. It has missing internal pipx metadata." in capsys.readouterr().err


@pytest.mark.parametrize(
    "metadata_version", [version for version in PIPX_METADATA_LEGACY_VERSIONS if version is not None]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_legacy_venv(metadata_version: str) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["upgrade", "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_suffix() -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_a"])

    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay_a"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_suffix_legacy_venv() -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_a"])
    mock_legacy_venv("pycowsay_a", metadata_version="0.1")

    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay_a"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])

    assert not run_pipx_cli(["upgrade", "isort"])

    assert f"upgraded package isort from {PKG['isort']['spec'].split('==')[-1]} to" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_missing_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["upgrade", "pycowsay"])

    err: Final[str] = capsys.readouterr().err
    assert ("invalid python interpreter" in err, "pipx reinstall-all" in err) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_reports_corrupt_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata_path: Final[Path] = paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME
    metadata: Final[dict[str, dict[str, str | None]]] = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["main_package"]["package_or_url"] = None
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert "package pycowsay has corrupt pipx metadata" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_ignores_venv_args_without_install(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    caplog.clear()

    assert not run_pipx_cli(["upgrade", "pycowsay", "--system-site-packages"])

    assert "Ignoring --system-site-packages as not combined with --install" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_editable(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", empty_project.as_posix(), "--force"])

    assert not run_pipx_cli(["upgrade", "--editable", "empty_project"])

    upgrade_out: Final[str] = " ".join(capsys.readouterr().out.split())  # pipx_wrap reflows messages across lines
    assert (
        "empty-project is unchanged at version" in upgrade_out,
        "installed from the local source" in upgrade_out,
        "no package index was checked" in upgrade_out,
    ) == (True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_local_path_does_not_claim_latest(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    # https://github.com/pypa/pipx/issues/2040: pipx consulted no index, so it cannot know the version is the latest
    assert not run_pipx_cli(["install", str(empty_project.resolve())])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", "empty_project"])

    upgrade_out: Final[str] = " ".join(capsys.readouterr().out.split())  # pipx_wrap reflows messages across lines
    assert (
        "is already at latest version" in upgrade_out,
        "empty-project is unchanged at version" in upgrade_out,
        "no package index was checked" in upgrade_out,
        "pipx install --force empty-project" in upgrade_out,
    ) == (False, True, True, True)


@pytest.mark.parametrize(
    ("flags", "injected_upgraded"),
    [
        pytest.param(["--include-injected"], True, id="include-injected"),
        pytest.param([], False, id="main-package-only"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected(
    capsys: pytest.CaptureFixture[str], flags: list[str], injected_upgraded: bool
) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    assert not run_pipx_cli(["inject", "isort", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", *flags, "isort"])

    out: Final[str] = capsys.readouterr().out
    assert ("upgraded package isort" in out, "upgraded package black" in out) == (True, injected_upgraded)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_uv_keeps_pinned_injected_dependency(tmp_path: Path) -> None:
    # uv's --upgrade re-resolves every dependency, unlike pip's default only-if-needed strategy
    index: Final[Path] = tmp_path / "index"
    write_wheel(index, "tool", "1.0", requires=("plug",))
    write_wheel(index, "plug", "1.0")
    write_wheel(index, "plug", "1.5")
    pip_args: Final[str] = f"--pip-args=--no-index --find-links {index}"
    assert not run_pipx_cli(["install", "--backend", "uv", pip_args, "tool"])
    assert not run_pipx_cli(["inject", pip_args, "tool", "plug==1.5"])
    assert not run_pipx_cli(["pin", "tool", "--injected-only"])
    write_wheel(index, "plug", "9.0")

    assert not run_pipx_cli(["upgrade", "tool"])

    assert sorted(path.name for path in (paths.CTX.venvs / "tool").rglob("plug-*.dist-info")) == ["plug-1.5.dist-info"]


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["upgrade", "empty-project"], id="upgrade"),
        pytest.param(["upgrade-all"], id="upgrade-all"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_removes_dropped_app(
    two_app_project: Path, command: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", str(two_app_project)])
    drop_extra_app(two_app_project)
    assert not run_pipx_cli(command)
    capsys.readouterr()

    assert not run_pipx_cli(["list"])

    assert (
        sorted(path.name for path in paths.CTX.bin_dir.iterdir()),
        "empty-project-extra" in capsys.readouterr().out,
    ) == ([app_name("empty-project")], False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected_removes_dropped_app(
    two_app_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--include-apps", "pycowsay", str(two_app_project)])
    drop_extra_app(two_app_project)
    assert not run_pipx_cli(["upgrade", "--include-injected", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--include-injected"])

    assert (
        sorted(path.name for path in paths.CTX.bin_dir.iterdir()),
        "empty-project-extra" in capsys.readouterr().out,
    ) == ([app_name("empty-project"), app_name("pycowsay")], False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected_with_suffix_keeps_package_name() -> None:
    # upgrading rewrites the injected record under the name pipx keys it by; re-appending the environment suffix there
    # renamed the package on every run ("black" -> "black@1" -> "black@1@1") until `pipx uninject` could not name it
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    assert not run_pipx_cli(["inject", "pycowsay@1", PKG["black"]["spec"], "--with-suffix"])
    assert not run_pipx_cli(["upgrade", "--include-injected", "pycowsay@1"])

    assert not run_pipx_cli(["uninject", "pycowsay@1", "black"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_missing(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install"])

    assert "installed package pycowsay" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_missing_honors_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    pkg_spec: Final[str] = PKG["isort"]["spec"]

    assert not run_pipx_cli(["upgrade", pkg_spec, "--install"])

    assert f"installed package isort {pkg_spec.split('==')[-1]}" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_multiple(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["upgrade", "isort", "pycowsay"])

    out: Final[str] = capsys.readouterr().out
    assert (
        f"upgraded package isort from {PKG['isort']['spec'].split('==')[-1]} to" in out,
        "pycowsay is already at latest version" in out,
    ) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_absolute_path(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    assert run_pipx_cli(["upgrade", "--verbose", str(empty_project.resolve())])

    assert "Package cannot be a URL" not in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_with_extras(capsys: pytest.CaptureFixture[str]) -> None:
    # https://github.com/pypa/pipx/issues/925
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "installed package pycowsay" in capsys.readouterr().out

    assert not run_pipx_cli(["upgrade", "pycowsay[test_extra]"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert ("pycowsay is already at latest version" in captured.out, "Package is not installed" in captured.err) == (
        True,
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_preserves_included_dependency(local_extras_wheel: Path) -> None:
    assert not run_pipx_cli(["install", f"{local_extras_wheel}[tools]", "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["upgrade", "repeatme"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


@pytest.mark.parametrize(
    ("upgrade_args", "expected_args"),
    [
        pytest.param([], ["--no-cache-dir"], id="preserves_stored"),
        pytest.param(["--pip-args=--no-deps"], ["--no-deps"], id="cli_overrides_stored"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_pip_args(upgrade_args: list[str], expected_args: list[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--pip-args=--no-cache-dir"])

    assert not run_pipx_cli(["upgrade", "pycowsay", *upgrade_args])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == expected_args


@pytest.mark.parametrize(
    ("command", "expected_options", "expected_cooldowns"),
    [
        pytest.param(["upgrade", "--include-injected", "pycowsay"], (True, True), (7, 5), id="stored"),
        pytest.param(
            ["upgrade-all", "--include-injected", "--cooldown", "0"],
            (False, False),
            (0, 0),
            id="override-all",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_cooldown(
    package_cache_dir: Path,
    empty_project_wheel: Path,
    caplog: pytest.LogCaptureFixture,
    *,
    command: list[str],
    expected_options: tuple[bool, bool],
    expected_cooldowns: tuple[int, int],
) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project_wheel)])
    caplog.clear()

    assert not run_pipx_cli(command)

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (
        "--uploaded-prior-to P7D" in caplog.text,
        "--uploaded-prior-to P5D" in caplog.text,
        (metadata.main_package.cooldown_days, metadata.injected_packages["empty-project"].cooldown_days),
    ) == (*expected_options, expected_cooldowns)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_injected_uses_stored_pip_args(empty_project_wheel: Path) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--pip-args=--no-cache-dir"])
    assert not run_pipx_cli(["inject", "pycowsay", str(empty_project_wheel), "--pip-args=--no-compile"])

    assert not run_pipx_cli(["upgrade", "--include-injected", "pycowsay"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (metadata.main_package.pip_args, metadata.injected_packages["empty-project"].pip_args) == (
        ["--no-cache-dir"],
        ["--no-compile"],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_json_stays_pure(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install", "--output", "json"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    # parsing fails if the internal install printed human text ahead of the document
    document: Final = json.loads(captured.out)
    assert (document["command"], document["status"], captured.err) == (["upgrade"], "success", "")


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_suffix_removes_link_named_before_the_last_dot(make_wheel: Callable[[dict[str, str]], Path]) -> None:
    wheel: Final[Path] = make_wheel({
        "foo_bar_x.py": "def main() -> None:\n    pass\n",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/entry_points.txt": "[console_scripts]\ntool3.12 = foo_bar_x:main\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })
    assert not run_pipx_cli(["install", "--suffix=@1", str(wheel)])
    # the name pipx 1.17.14 gave the link, with the suffix before the last dot
    (paths.CTX.bin_dir / "tool3@1.12").symlink_to(paths.CTX.venvs / "foo-bar-x@1" / "bin" / "tool3.12")

    assert not run_pipx_cli(["upgrade", "foo-bar-x@1"])

    assert sorted(path.name for path in paths.CTX.bin_dir.iterdir()) == ["tool3.12@1"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_local_source_hides_url_credentials(
    credentialed_wheel_url: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", credentialed_wheel_url])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", "foo-bar-x"])

    out: Final[str] = capsys.readouterr().out
    assert (
        f"local source {redact_url_credentials(credentialed_wheel_url)};" in " ".join(out.split()),
        "s3cr3ttok" in out,
    ) == (True, False)


@pytest.fixture
def credentialed_wheel_url(dotted_app_wheel: Path) -> Iterator[str]:
    handler: Final = partial(SimpleHTTPRequestHandler, directory=str(dotted_app_wheel.parent))
    # not http.server.HTTPServer: its bind resolves the host name, which stalls for 30 s on macOS CI runners
    with ThreadingTCPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://u:s3cr3ttok@127.0.0.1:{server.server_address[1]}/{dotted_app_wheel.name}"
        finally:
            server.shutdown()


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_ignores_pip_config_shipped_by_wheel(make_wheel: Callable[[dict[str, str]], Path]) -> None:
    wheel: Final[Path] = make_wheel({
        "foo_bar_x.py": "def main() -> None:\n    pass\n",
        # data files unpack into the venv root, where pip reads its site configuration
        **{f"foo_bar_x-1.data/data/{name}": "[install]\ntarget = ../escaped\n" for name in ("pip.conf", "pip.ini")},
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/entry_points.txt": "[console_scripts]\ntool = foo_bar_x:main\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })
    assert not run_pipx_cli(["install", str(wheel)])

    assert not run_pipx_cli(["upgrade", "foo-bar-x"])

    assert not (paths.CTX.venvs / "escaped").exists()
