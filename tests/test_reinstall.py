from __future__ import annotations

import importlib
import json
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import replace
from typing import TYPE_CHECKING, Final

import pytest

from helpers import (
    PACKAGE_CACHE_DIR_NAME,
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    mock_legacy_venv,
    module_version,
    run_pipx_cli,
    skip_if_windows,
    write_wheel,
)
from package_info import PKG
from pipx import paths, util, venv_inspect
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata
from pipx.util import redact_url_credentials

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


@pytest.mark.skipif(sys.version_info < (3, 15), reason="lazy imports require Python 3.15")
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_self_resolves_lazy_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    venv_dir = paths.ctx.venvs / "pycowsay"
    (venv_dir / "reinstall_import_source.py").write_text("VALUE = 'resolved'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(venv_dir))
    module = importlib.import_module("pipx.commands.reinstall")
    exec(  # ruff:ignore[exec-builtin]  # keep Python 3.15 syntax parseable on older versions
        "lazy from reinstall_import_source import VALUE as reinstall_import_value", vars(module)
    )
    monkeypatch.setattr(sys, "prefix", str(venv_dir))

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])
    assert getattr(module, "reinstall_import_value", None) == "resolved"


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_inline_script(inline_script: Path) -> None:
    assert not run_pipx_cli(["install", str(inline_script)])
    inline_script.write_text(
        inline_script.read_text(encoding="utf-8").replace("installed", "reinstalled"),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "hello"])

    process: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [paths.ctx.bin_dir / app_name("hello")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert process.stdout == "reinstalled\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_preserves_cooldowns(
    root: Path,
    empty_project_wheel: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    find_links: Final[Path] = root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, "pycowsay"])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project_wheel)])
    caplog.clear()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        "--uploaded-prior-to P7D" in caplog.text,
        "--uploaded-prior-to P5D" in caplog.text,
        metadata.main_package.cooldown_days,
        metadata.injected_packages["empty-project"].cooldown_days,
    ) == (True, True, 7, 5)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_pylock_restores_source_after_build_failure(
    make_pylock: Callable[[str, str], Path],
    make_project_with_dependency: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = make_project_with_dependency("pycowsay==0.0.0.2")
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), str(project)])
    capsys.readouterr()
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace("flit_core.buildapi", "missing"),
        encoding="utf-8",
    )

    assert run_pipx_cli(["reinstall", "empty-project"])

    metadata = PipxMetadata(paths.ctx.venvs / "empty-project").main_package
    err = capsys.readouterr().err
    assert (
        "Reinstall failed; restored empty-project" in err,
        "Traceback" in err,
        metadata.package_version,
        metadata.lock_file,
        (paths.ctx.bin_dir / app_name("empty-project")).exists(),
    ) == (True, False, "0.1.0", lock_file.resolve(), True)


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_global() -> None:
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--global", "--python", sys.executable, "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_nonexistent(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["reinstall", "--python", sys.executable, "nonexistent"])
    assert "Nothing to reinstall for nonexistent" in capsys.readouterr().out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_legacy_venv(metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_legacy_venv_inspects_once_for_resources(mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")
    mock_legacy_venv("pycowsay")
    run_subprocess = mocker.spy(venv_inspect, "run_subprocess")

    assert run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"]) == 0

    assert executable_path.exists()
    assert run_subprocess.call_count == 2


def _record_from_newer_pipx(venv_dir: Path) -> None:
    record: Final[Path] = venv_dir / "pipx_metadata.json"
    record.write_text(
        json.dumps(json.loads(record.read_text(encoding="utf-8")) | {"pipx_metadata_version": "99.0"}), encoding="utf-8"
    )


def _killed_before_recording(venv_dir: Path) -> None:
    (venv_dir / "pipx_metadata.json").unlink()
    (venv_dir / "pipx_unfinished").touch()


def _killed_before_installing(venv_dir: Path) -> None:
    (venv_dir / "pipx_metadata.json").unlink()
    for dist_info in venv_dir.rglob("pycowsay-*.dist-info"):
        shutil.rmtree(dist_info)


def _killed_while_creating(venv_dir: Path) -> None:
    shutil.rmtree(venv_dir)
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").touch()


@pytest.mark.parametrize(
    "lose_record",
    [
        pytest.param(_record_from_newer_pipx, id="record-from-newer-pipx"),
        pytest.param(_killed_before_recording, id="killed-before-recording"),
        pytest.param(_killed_before_installing, id="killed-before-installing"),
        pytest.param(_killed_while_creating, id="killed-while-creating"),
    ],
)
@pytest.mark.parametrize(
    "command",
    [pytest.param(["reinstall", "pycowsay"], id="reinstall"), pytest.param(["reinstall-all"], id="reinstall-all")],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_refuses_to_guess_source_of_unrecorded_venv(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    lose_record: Callable[[Path], None],
    command: list[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    lose_record(paths.ctx.venvs / "pycowsay")
    install = mocker.patch("pipx.commands.reinstall.install", autospec=True)
    capsys.readouterr()

    assert run_pipx_cli(command)

    assert "Not reinstalling pycowsay. It has missing internal pipx metadata" in capsys.readouterr().err
    install.assert_not_called()
    assert (paths.ctx.venvs / "pycowsay").is_dir()


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_suffix() -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_suffix_legacy_venv(metadata_version: str) -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_injected_package_suffix() -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    assert not run_pipx_cli(["inject", "pycowsay@1", PKG["black"]["spec"], "--with-suffix", "--include-apps"])

    assert not run_pipx_cli(["reinstall", "pycowsay@1"])

    assert sorted(path.name for path in paths.ctx.bin_dir.iterdir()) == sorted(
        app_name(app) for app in ("black@1", "blackd@1", "pycowsay@1")
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "isort==5.6.4"])

    # clear capsys before reinstall
    captured = capsys.readouterr()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "isort"])
    captured = capsys.readouterr()
    assert "installed package isort 5.6.4" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_preserves_included_dependency(local_extras_wheel: Path) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "repeatme"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_removes_stale_apps_after_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    venv_dir = paths.ctx.venvs / "pycowsay"
    stale_app_name = app_name("removed-cowsay")
    stale_app_path = util.get_venv_paths(venv_dir)[0] / stale_app_name
    stale_app_path.write_text("#!/bin/sh\n")
    stale_app_path.chmod(0o755)

    stale_exposed_path = paths.ctx.bin_dir / stale_app_name
    stale_exposed_path.symlink_to(stale_app_path)

    metadata = PipxMetadata(venv_dir)
    metadata.main_package = replace(
        metadata.main_package,
        apps=[*metadata.main_package.apps, stale_app_name],
        app_paths=[*metadata.main_package.app_paths, stale_app_path],
    )
    metadata.write()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert not stale_exposed_path.exists()
    assert not stale_exposed_path.is_symlink()


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_with_path(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / "some" / "path"

    assert run_pipx_cli(["reinstall", str(path)])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")

    assert run_pipx_cli(["reinstall", str(path.resolve())])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_pinned_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["pin", "black"])
    assert run_pipx_cli(["reinstall", "black"])
    captured = capsys.readouterr()
    assert "pinned" in captured.err

    assert not run_pipx_cli(["unpin", "black"])
    assert not run_pipx_cli(["reinstall", "black"])
    captured = capsys.readouterr()
    assert "installed package black" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_injected_pin() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert PipxMetadata(paths.ctx.venvs / "pycowsay").injected_packages["black"].pinned


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_quiet_says_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable, "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_json_reports_the_environments(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable, "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": ["reinstall-all"],
        "data": {"environments": [{"environment": "pycowsay"}]},
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_json_reports_a_missing_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["reinstall", "--python", sys.executable, "--output", "json", "missing"])

    payload: Final[dict[str, object]] = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_json_reports_returned_errors(capsys: pytest.CaptureFixture[str], partial: bool) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    if partial:
        assert not run_pipx_cli(["install", "pycowsay", "--suffix=-other"])
    python = util.get_venv_paths(paths.ctx.venvs / "pycowsay")[1]
    capsys.readouterr()

    assert run_pipx_cli(["reinstall-all", "--python", str(python), "--output", "json"]) == 1

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == ("partial" if partial else "error")
    assert result["data"]["environments"] == ([{"environment": "pycowsay-other"}] if partial else [])
    assert len(result["errors"]) == 1
    assert result["errors"][0]["environment"] == "pycowsay"
    assert result["errors"][0]["code"] == "environment_reinstall_failed"
    assert "the python executable would be deleted" in result["errors"][0]["message"]
    assert python.is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_json_reports_no_environments(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable, "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {"environments": []}


@pytest.fixture
def installed_with_injection(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # requested for its isolated pipx home
    capsys: pytest.CaptureFixture[str],
) -> pytest.CaptureFixture[str]:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()
    return capsys


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        pytest.param(["reinstall", "pycowsay"], "reinstall", id="reinstall"),
        pytest.param(["reinstall-all"], "reinstall-all", id="reinstall-all"),
    ],
)
def test_reinstall_json_with_injected_package_prints_only_the_envelope(
    installed_with_injection: pytest.CaptureFixture[str],
    argv: list[str],
    command: str,
) -> None:
    assert not run_pipx_cli([*argv, "--python", sys.executable, "--output", "json"])

    assert json.loads(installed_with_injection.readouterr().out) == {
        "command": [command],
        "data": {"environments": [{"environment": "pycowsay"}]},
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


def test_reinstall_reports_the_reinjected_package(installed_with_injection: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert "injected package black into venv pycowsay" in installed_with_injection.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_records_injected_local_project_under_its_new_name(
    empty_project_wheel: Path, local_extras_project: Path
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", str(empty_project_wheel)])
    assert not run_pipx_cli(["inject", "--include-apps", "empty-project", str(local_extras_project)])
    pyproject: Final[Path] = local_extras_project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('name = "repeatme"', 'name = "renamed"')
        + '[tool.flit.module]\nname = "repeatme"\n',
        encoding="utf-8",
    )

    assert not run_pipx_cli(["reinstall", "empty-project"])

    assert list(PipxMetadata(paths.ctx.venvs / "empty-project").injected_packages) == ["renamed"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_main_package_a_plugin_depends_on(tmp_path: Path) -> None:
    plugin_index: Final[Path] = tmp_path / "plugin-index"
    write_wheel(plugin_index, "plugin", "1.0", requires=("tool",))
    write_wheel(plugin_index, "tool", "99.0")
    local_tool: Final[Path] = write_wheel(tmp_path / "local", "tool", "1.0")
    assert not run_pipx_cli(["install", "--backend", "pip", str(local_tool)])
    assert not run_pipx_cli(["inject", "tool", "plugin", f"--pip-args=--no-index --find-links={plugin_index}"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "tool"])

    assert module_version("tool") == "1.0"


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers")
def test_reinstall_restores_venv_on_sigterm_to_pipx_alone(
    capsys: pytest.CaptureFixture[str], before_venv_subprocess: Callable[[Path, Callable[[], None]], None]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    metadata_before: Final[str] = (paths.ctx.venvs / "pycowsay" / "pipx_metadata.json").read_text()
    before_venv_subprocess(paths.ctx.venvs / "pycowsay", lambda: os.kill(os.getpid(), signal.SIGTERM))

    exit_code: Final[int] = run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert (exit_code, (paths.ctx.venvs / "pycowsay" / "pipx_metadata.json").read_text()) == (1, metadata_before)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_injected_package_without_source_hides_url_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    index: Final[str] = "--index-url=https://u:s3cr3ttok@host/simple"
    metadata.injected_packages["helper"] = replace(
        metadata.main_package, package="helper", package_or_url=None, pip_args=[index]
    )
    metadata.write()
    capsys.readouterr()

    assert run_pipx_cli(["reinstall", "pycowsay"])

    err: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (redact_url_credentials(index) in err, "s3cr3ttok" in err) == (True, False)
