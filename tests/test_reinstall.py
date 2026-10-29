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
    PIPX_METADATA_LEGACY_VERSIONS,
    SKIP_IF_WINDOWS,
    app_name,
    mock_legacy_venv,
    module_version,
    run_pipx_cli,
    write_wheel,
)
from package_info import PKG
from pipx import paths, util, venv_inspect
from pipx.commands import common
from pipx.commands import reinstall as reinstall_module
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, PipxMetadata
from pipx.util import redact_url_credentials

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import ModuleType
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_resolves_recorded_relative_find_links_in_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(metadata.main_package, pip_args=["--find-links", "wheels"])
    metadata.write()
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["reinstall", "pycowsay"])

    assert PipxMetadata(venv_dir).main_package.pip_args == ["--find-links", str((venv_dir / "wheels").resolve())]


@SKIP_IF_WINDOWS
def test_reinstall_refuses_recorded_find_links_writable_by_others(
    shared_find_links: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()

    assert run_pipx_cli(["reinstall", "pycowsay"])

    assert (
        f"another account can change {shared_find_links}, and with it what gets installed." in capsys.readouterr().err
    )


@pytest.fixture
def shared_find_links(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
) -> Path:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    (shared := tmp_path.resolve() / "shared").mkdir()
    shared.chmod(0o777)
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    metadata.main_package = replace(metadata.main_package, pip_args=["--find-links", str(shared / "wheels")])
    metadata.write()
    return shared


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("shared_find_links")
def test_reinstall_keeps_environment_of_refused_find_links() -> None:
    metadata_file: Final[Path] = paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME
    recorded: Final[bytes] = metadata_file.read_bytes()

    run_pipx_cli(["reinstall", "pycowsay"])

    assert metadata_file.read_bytes() == recorded


@pytest.mark.skipif(sys.version_info < (3, 15), reason="lazy imports require Python 3.15")
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_self_resolves_lazy_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    (venv_dir / "reinstall_import_source.py").write_text("VALUE = 'resolved'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(venv_dir))
    module: Final[ModuleType] = importlib.import_module("pipx.commands.reinstall")
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

    assert (
        subprocess.run([paths.CTX.bin_dir / app_name("hello")], check=True, capture_output=True, text=True).stdout
        == "reinstalled\n"
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_preserves_cooldowns(
    package_cache_dir: Path,
    empty_project_wheel: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, "pycowsay"])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project_wheel)])
    caplog.clear()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
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
    project: Final[Path] = make_project_with_dependency("pycowsay==0.0.0.2")
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), str(project)])
    capsys.readouterr()
    pyproject: Final[Path] = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace("flit_core.buildapi", "missing"),
        encoding="utf-8",
    )

    assert run_pipx_cli(["reinstall", "empty-project"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "empty-project").main_package
    err: Final[str] = capsys.readouterr().err
    assert (
        "Reinstall failed; restored empty-project" in err,
        "Traceback" in err,
        metadata.package_version,
        metadata.lock_file,
        (paths.CTX.bin_dir / app_name("empty-project")).exists(),
    ) == (True, False, "0.1.0", lock_file.resolve(), True)


@SKIP_IF_WINDOWS
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
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    run_subprocess: Final[MagicMock] = mocker.spy(venv_inspect, "run_subprocess")

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert ((paths.CTX.bin_dir / app_name("pycowsay")).exists(), run_subprocess.call_count) == (True, 2)


def _record_from_newer_pipx(venv_dir: Path) -> None:
    record: Final[Path] = venv_dir / PIPX_INFO_FILENAME
    record.write_text(
        json.dumps(json.loads(record.read_text(encoding="utf-8")) | {"pipx_metadata_version": "99.0"}), encoding="utf-8"
    )


def _killed_before_recording(venv_dir: Path) -> None:
    (venv_dir / PIPX_INFO_FILENAME).unlink()
    (venv_dir / "pipx_unfinished").touch()


def _killed_before_installing(venv_dir: Path) -> None:
    (venv_dir / PIPX_INFO_FILENAME).unlink()
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
    lose_record(paths.CTX.venvs / "pycowsay")
    install: Final[MagicMock] = mocker.patch("pipx.commands.reinstall.install", autospec=True)
    capsys.readouterr()

    assert run_pipx_cli(command)

    assert (
        "Not reinstalling pycowsay. It has missing internal pipx metadata" in capsys.readouterr().err,
        install.called,
        (paths.CTX.venvs / "pycowsay").is_dir(),
    ) == (True, False, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_suffix() -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay_x"])


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_a_dropped_app_name_taken_over_during_the_rebuild(
    make_wheel: Callable[[dict[str, str]], Path],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    tmp_path: Path,
) -> None:
    def release(*apps: str) -> Path:
        entry_points: Final[str] = "".join(f"{app} = foo_bar_x:main\n" for app in apps)
        return make_wheel({
            "foo_bar_x.py": "def main() -> None:\n    pass\n",
            "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
            "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            "foo_bar_x-1.dist-info/entry_points.txt": f"[console_scripts]\n{entry_points}",
            "foo_bar_x-1.dist-info/RECORD": "",
        })

    assert not run_pipx_cli(["install", str(release("tool", "shared"))])
    release("tool")
    shared: Final[Path] = paths.CTX.bin_dir / "shared"
    (other := tmp_path / "other").touch()

    def take_over_dangling_name() -> None:
        if not shared.exists():
            shared.unlink()
            shared.symlink_to(other)

    before_venv_subprocess(paths.CTX.venvs / "foo-bar-x", take_over_dangling_name)

    assert not run_pipx_cli(["reinstall", "foo-bar-x"])

    assert shared.resolve() == other.resolve()


@pytest.mark.parametrize(
    "symlinks", [pytest.param(True, id="symlink", marks=SKIP_IF_WINDOWS), pytest.param(False, id="copy")]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_a_file_it_did_not_expose(
    dotted_app_wheel: Path, mocker: MockerFixture, symlinks: bool
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=symlinks)
    paths.CTX.bin_dir.mkdir(parents=True, exist_ok=True)
    (user_file := paths.CTX.bin_dir / app_name("tool3.12")).write_text("mine", encoding="utf-8")
    assert not run_pipx_cli(["install", str(dotted_app_wheel)])

    assert not run_pipx_cli(["reinstall", "foo-bar-x"])

    assert (user_file.is_symlink(), user_file.read_text(encoding="utf-8")) == (False, "mine")


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_refreshes_a_stale_copy_it_exposed(dotted_app_wheel: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    assert not run_pipx_cli(["install", str(dotted_app_wheel)])
    exposed: Final[Path] = paths.CTX.bin_dir / app_name("tool3.12")
    exposed.write_bytes(exposed.read_bytes() + b"# stale\n")

    assert not run_pipx_cli(["reinstall", "foo-bar-x"])

    # Windows launchers embed their build time, so compare with the launcher this reinstall wrote
    assert exposed.read_bytes() == (util.get_venv_paths(paths.CTX.venvs / "foo-bar-x")[0] / exposed.name).read_bytes()


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_suffix_legacy_venv() -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])
    mock_legacy_venv("pycowsay_x", metadata_version="0.1")

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay_x"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_injected_package_suffix() -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    assert not run_pipx_cli(["inject", "pycowsay@1", PKG["black"]["spec"], "--with-suffix", "--include-apps"])

    assert not run_pipx_cli(["reinstall", "pycowsay@1"])

    assert sorted(path.name for path in paths.CTX.bin_dir.iterdir()) == sorted(
        app_name(app) for app in ("black@1", "blackd@1", "pycowsay@1")
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "isort==5.6.4"])
    capsys.readouterr()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "isort"])

    assert "installed package isort 5.6.4" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_preserves_included_dependency(local_extras_wheel: Path) -> None:
    assert not run_pipx_cli(["install", f"{local_extras_wheel}[tools]", "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "repeatme"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_removes_stale_apps_after_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    stale_app_name: Final[str] = app_name("removed-cowsay")
    (stale_app_path := util.get_venv_paths(venv_dir)[0] / stale_app_name).write_text("#!/bin/sh\n")
    stale_app_path.chmod(0o755)
    (stale_exposed_path := paths.CTX.bin_dir / stale_app_name).symlink_to(stale_app_path)
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(
        metadata.main_package,
        apps=[*metadata.main_package.apps, stale_app_name],
        app_paths=[*metadata.main_package.app_paths, stale_app_path],
    )
    metadata.write()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert (stale_exposed_path.exists(), stale_exposed_path.is_symlink()) == (False, False)


@pytest.mark.parametrize(
    "spell", [pytest.param(lambda path: path, id="as-given"), pytest.param(lambda path: path.resolve(), id="resolved")]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_with_path(capsys: pytest.CaptureFixture[str], tmp_path: Path, spell: Callable[[Path], Path]) -> None:
    assert run_pipx_cli(["reinstall", str(spell(tmp_path / "some" / "path"))])

    assert "Expected the name of an installed package" in capsys.readouterr().err.replace("\n", " ")


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_pinned_package_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["pin", "black"])

    assert run_pipx_cli(["reinstall", "black"])

    assert "pinned" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_unpinned_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["unpin", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["reinstall", "black"])

    assert "installed package black" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_injected_pin() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").injected_packages["black"].pinned


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

    assert json.loads(capsys.readouterr().out)["status"] == "error"


@pytest.mark.parametrize(
    ("suffixes", "status", "environments"),
    [
        pytest.param([], "error", [], id="error"),
        pytest.param(["-other"], "partial", [{"environment": "pycowsay-other"}], id="partial"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_json_reports_returned_errors(
    capsys: pytest.CaptureFixture[str], suffixes: list[str], status: str, environments: list[dict[str, str]]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    for suffix in suffixes:
        assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    python: Final[Path] = util.get_venv_paths(paths.CTX.venvs / "pycowsay")[1]
    capsys.readouterr()

    assert run_pipx_cli(["reinstall-all", "--python", str(python), "--output", "json"]) == 1

    result: Final = json.loads(capsys.readouterr().out)
    assert (
        result["status"],
        result["data"]["environments"],
        [(error["environment"], error["code"]) for error in result["errors"]],
        "the python executable would be deleted" in result["errors"][0]["message"],
        python.is_file(),
    ) == (status, environments, [("pycowsay", "environment_reinstall_failed")], True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_json_reports_no_environments(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable, "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {"environments": []}


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


@pytest.fixture
def installed_with_injection(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # requested for its isolated pipx home
    capsys: pytest.CaptureFixture[str],
) -> pytest.CaptureFixture[str]:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()
    return capsys


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

    assert list(PipxMetadata(paths.CTX.venvs / "empty-project").injected_packages) == ["renamed"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_keeps_main_package_a_plugin_depends_on(tmp_path: Path) -> None:
    plugin_index: Final[Path] = tmp_path / "plugin-index"
    write_wheel(plugin_index, "plugin", "1.0", requires=("tool",))
    write_wheel(plugin_index, "tool", "99.0")
    assert not run_pipx_cli(["install", "--backend", "pip", str(write_wheel(tmp_path / "local", "tool", "1.0"))])
    assert not run_pipx_cli(["inject", "tool", "plugin", f"--pip-args=--no-index --find-links={plugin_index}"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "tool"])

    assert module_version("tool") == "1.0"


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers")
def test_reinstall_restores_venv_on_sigterm_to_pipx_alone(
    capsys: pytest.CaptureFixture[str], before_venv_subprocess: Callable[[Path, Callable[[], None]], None]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    metadata_before: Final[str] = (paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME).read_text()
    before_venv_subprocess(paths.CTX.venvs / "pycowsay", lambda: os.kill(os.getpid(), signal.SIGTERM))

    exit_code: Final[int] = run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert (exit_code, (paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME).read_text()) == (1, metadata_before)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers")
def test_reinstall_finishes_the_restore_through_a_second_signal(
    mocker: MockerFixture, before_venv_subprocess: Callable[[Path, Callable[[], None]], None]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata_before: Final[str] = (record := paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME).read_text()
    before_venv_subprocess(paths.CTX.venvs / "pycowsay", lambda: os.kill(os.getpid(), signal.SIGTERM))

    def rmdir_then_interrupt(path: Path, *, safe_rm: bool = True) -> None:
        util.rmdir(path, safe_rm=safe_rm)
        signal.raise_signal(signal.SIGINT)

    mocker.patch.object(reinstall_module, "rmdir", autospec=True, side_effect=rmdir_then_interrupt)

    run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert record.read_text() == metadata_before


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_injected_package_without_source_hides_url_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    index: Final[str] = "--index-url=https://u:s3cr3ttok@host/simple"
    metadata.injected_packages["helper"] = replace(
        metadata.main_package, package="helper", package_or_url=None, pip_args=[index]
    )
    metadata.write()
    capsys.readouterr()

    assert run_pipx_cli(["reinstall", "pycowsay"])

    err: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (redact_url_credentials(index) in err, "s3cr3ttok" in err) == (True, False)
