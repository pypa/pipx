from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import zipfile
from dataclasses import replace
from typing import TYPE_CHECKING, Final, cast

import pytest

from helpers import (
    PACKAGE_CACHE_DIR_NAME,
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    drop_extra_app,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    set_shared_pip_age,
    skip_if_windows,
    unwrap_log_text,
)
from package_info import PKG
from pipx import paths, shared_libs
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from _pytest.capture import CaptureResult


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    captured = capsys.readouterr()
    assert "Package is not installed" in captured.err

    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay"])
    captured = capsys.readouterr()
    assert "pycowsay is already at latest version" in captured.out


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
def test_upgrade_refreshes_shared_pip_only_when_due(
    monkeypatch: pytest.MonkeyPatch, age_sec: float, disable_auto_upgrade: str, upgrade_args: list[str], refreshed: bool
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, disable_auto_upgrade)
    last_upgrade: Final[float] = set_shared_pip_age(age_sec)

    assert not run_pipx_cli(["upgrade", "pycowsay", *upgrade_args])

    assert (shared_libs.shared_libs.pip_path.stat().st_mtime != last_upgrade) is refreshed


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_records_relative_find_links_as_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["upgrade", "pycowsay", "--pip-args=--find-links wheels"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert metadata.main_package.pip_args == ["--find-links", str((tmp_path / "wheels").resolve())]


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_resolves_recorded_relative_find_links_in_venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    venv_dir: Final[Path] = paths.ctx.venvs / "pycowsay"
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(metadata.main_package, pip_args=["--find-links", "wheels"])
    metadata.write()
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert PipxMetadata(venv_dir).main_package.pip_args == ["--find-links", str((venv_dir / "wheels").resolve())]


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_inline_script(inline_script: Path) -> None:
    assert not run_pipx_cli(["install", "--app", "greet", str(inline_script)])
    inline_script.write_text(
        inline_script.read_text(encoding="utf-8").replace("installed", "upgraded"),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["upgrade", "greet"])

    process: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [paths.ctx.bin_dir / app_name("greet")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert process.stdout == "upgraded\n"


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

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["upgrade"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.ctx.venvs / "pycowsay"),
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
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(command)

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (
        "Not upgrading locked package pycowsay. Update its lock file and run `pipx reinstall pycowsay`."
        in unwrap_log_text(capsys.readouterr().out),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_global(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["upgrade", "--global", "pycowsay"])
    captured = capsys.readouterr()
    assert "Package is not installed" in captured.err

    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out

    assert not run_pipx_cli(["upgrade", "--global", "pycowsay"])
    captured = capsys.readouterr()
    assert "pycowsay is already at latest version" in captured.out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_legacy_venv(capsys: pytest.CaptureFixture[str], metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    captured = capsys.readouterr()
    if metadata_version is None:
        assert run_pipx_cli(["upgrade", "pycowsay"])
        captured = capsys.readouterr()
        assert "Not upgrading pycowsay. It has missing internal pipx metadata." in captured.err
    else:
        assert not run_pipx_cli(["upgrade", "pycowsay"])
        captured = capsys.readouterr()


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_suffix() -> None:
    name = "pycowsay"
    suffix = "_a"

    assert not run_pipx_cli(["install", name, f"--suffix={suffix}"])
    assert run_pipx_cli(["upgrade", f"{name}"])
    assert not run_pipx_cli(["upgrade", f"{name}{suffix}"])


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_suffix_legacy_venv(metadata_version: str) -> None:
    name = "pycowsay"
    suffix = "_a"

    assert not run_pipx_cli(["install", name, f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert run_pipx_cli(["upgrade", f"{name}"])
    assert not run_pipx_cli(["upgrade", f"{name}{suffix}"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    name = "isort"
    pkg_spec = PKG[name]["spec"]
    initial_version = pkg_spec.split("==")[-1]

    assert not run_pipx_cli(["install", f"{pkg_spec}"])
    assert not run_pipx_cli(["upgrade", f"{name}"])
    captured = capsys.readouterr()
    assert f"upgraded package {name} from {initial_version} to" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_missing_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    remove_venv_interpreter("pycowsay")

    result = run_pipx_cli(["upgrade", "pycowsay"])
    assert result != 0, "upgrade should fail when Python interpreter is missing"
    captured = capsys.readouterr()
    assert "invalid python interpreter" in captured.err
    assert "pipx reinstall-all" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_reports_corrupt_package(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    metadata_path: Final[Path] = paths.ctx.venvs / "pycowsay" / PIPX_INFO_FILENAME
    metadata: Final[dict[str, dict[str, str | None]]] = cast(
        "dict[str, dict[str, str | None]]",
        json.loads(metadata_path.read_text(encoding="utf-8")),
    )
    metadata["main_package"]["package_or_url"] = None
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert "package pycowsay has corrupt pipx metadata" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_ignores_venv_args_without_install(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    caplog.clear()

    assert not run_pipx_cli(["upgrade", "pycowsay", "--system-site-packages"])

    assert "Ignoring --system-site-packages as not combined with --install" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_editable(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    empty_project_path_as_string = empty_project.as_posix()
    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string, "--force"])
    assert not run_pipx_cli(["upgrade", "--editable", "empty_project"])
    captured = capsys.readouterr()
    upgrade_out = " ".join(captured.out.split())  # pipx_wrap reflows messages across lines
    assert "empty-project is unchanged at version" in upgrade_out
    assert "installed from the local source" in upgrade_out
    assert "no package index was checked" in upgrade_out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_local_path_does_not_claim_latest(
    capsys: pytest.CaptureFixture[str],
    empty_project: Path,
) -> None:
    """Regression test for https://github.com/pypa/pipx/issues/2040

    Upgrading a local-path install must not claim the package is at the
    *latest* version: no index was ever consulted.
    """
    assert not run_pipx_cli(["install", str(empty_project.resolve())])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade", "empty_project"])
    captured = capsys.readouterr()
    upgrade_out = " ".join(captured.out.split())  # pipx_wrap reflows messages across lines
    assert "is already at latest version" not in upgrade_out
    assert "empty-project is unchanged at version" in upgrade_out
    assert "no package index was checked" in upgrade_out
    assert "pipx install --force empty-project" in upgrade_out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    assert not run_pipx_cli(["inject", "isort", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "--include-injected", "isort"])
    captured = capsys.readouterr()
    assert "upgraded package isort" in captured.out
    assert "upgraded package black" in captured.out


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_uv_keeps_pinned_injected_dependency(tmp_path: Path) -> None:
    # uv's --upgrade re-resolves every dependency, unlike pip's default only-if-needed strategy
    index: Final[Path] = tmp_path / "index"
    index.mkdir()
    _publish_wheel(index, "tool", "1.0", requires=("plug",))
    _publish_wheel(index, "plug", "1.0")
    _publish_wheel(index, "plug", "1.5")
    find_links: Final[str] = f"--pip-args=--no-index --find-links {index}"
    assert not run_pipx_cli(["install", "--backend", "uv", find_links, "tool"])
    assert not run_pipx_cli(["inject", find_links, "tool", "plug==1.5"])
    assert not run_pipx_cli(["pin", "tool", "--injected-only"])
    _publish_wheel(index, "plug", "9.0")

    assert not run_pipx_cli(["upgrade", "tool"])

    assert sorted(path.name for path in (paths.ctx.venvs / "tool").rglob("plug-*.dist-info")) == ["plug-1.5.dist-info"]


def _publish_wheel(directory: Path, project: str, version: str, requires: tuple[str, ...] = ()) -> None:
    dist_info: Final[str] = f"{project}-{version}.dist-info"
    requires_dist: Final[str] = "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
    with zipfile.ZipFile(directory / f"{project}-{version}-py3-none-any.whl", "w") as wheel:
        wheel.writestr(f"{project}.py", "def main() -> None:\n    pass\n")
        wheel.writestr(
            f"{dist_info}/METADATA", f"Metadata-Version: 2.1\nName: {project}\nVersion: {version}\n{requires_dist}"
        )
        wheel.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        wheel.writestr(f"{dist_info}/entry_points.txt", f"[console_scripts]\n{project}-app = {project}:main\n")
        wheel.writestr(f"{dist_info}/RECORD", "")


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
        sorted(path.name for path in paths.ctx.bin_dir.iterdir()),
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
        sorted(path.name for path in paths.ctx.bin_dir.iterdir()),
        "empty-project-extra" in capsys.readouterr().out,
    ) == ([app_name("empty-project"), app_name("pycowsay")], False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected_with_suffix_keeps_package_name() -> None:
    # Regression: upgrading rewrites the injected record under the name pipx keys
    # it by, so re-appending the environment suffix there renamed the package on
    # every run ("black" -> "black@1" -> "black@1@1") until `pipx uninject` could
    # no longer name it.
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    assert not run_pipx_cli(["inject", "pycowsay@1", PKG["black"]["spec"], "--with-suffix"])
    assert not run_pipx_cli(["upgrade", "--include-injected", "pycowsay@1"])

    assert not run_pipx_cli(["uninject", "pycowsay@1", "black"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_no_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    assert not run_pipx_cli(["inject", "isort", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "isort"])
    captured = capsys.readouterr()
    assert "upgraded package isort" in captured.out
    assert "upgraded package black" not in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_missing(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_missing_honors_specifier(capsys: pytest.CaptureFixture[str]) -> None:
    pkg_spec = PKG["isort"]["spec"]
    assert not run_pipx_cli(["upgrade", pkg_spec, "--install"])
    captured = capsys.readouterr()
    assert f"installed package isort {pkg_spec.split('==')[-1]}" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_multiple(capsys: pytest.CaptureFixture[str]) -> None:
    name = "isort"
    pkg_spec = PKG[name]["spec"]
    initial_version = pkg_spec.split("==")[-1]
    assert not run_pipx_cli(["install", pkg_spec])

    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["upgrade", name, "pycowsay"])
    captured = capsys.readouterr()
    assert f"upgraded package {name} from {initial_version} to" in captured.out
    assert "pycowsay is already at latest version" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_absolute_path(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    assert run_pipx_cli(["upgrade", "--verbose", str(empty_project.resolve())])
    captured = capsys.readouterr()
    assert "Package cannot be a URL" not in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_with_extras(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that upgrading a package with extras in the name works correctly.

    Regression test for https://github.com/pypa/pipx/issues/925
    """
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay[test_extra]"])
    captured = capsys.readouterr()
    assert "pycowsay is already at latest version" in captured.out
    assert "Package is not installed" not in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_preserves_included_dependency(local_extras_wheel: Path) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["upgrade", "repeatme"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


@pytest.mark.parametrize(
    ("upgrade_args", "expected_args", "unexpected_args"),
    [
        pytest.param([], ["--no-cache-dir"], [], id="preserves_stored"),
        pytest.param(["--pip-args=--no-deps"], ["--no-deps"], ["--no-cache-dir"], id="cli_overrides_stored"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_pip_args(
    upgrade_args: list[str],
    expected_args: list[str],
    unexpected_args: list[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--pip-args=--no-cache-dir"])

    assert not run_pipx_cli(["upgrade", "pycowsay", *upgrade_args])

    pipx_venvs_dir = paths.ctx.home / "venvs"
    metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    for arg in expected_args:
        assert arg in metadata.main_package.pip_args
    for arg in unexpected_args:
        assert arg not in metadata.main_package.pip_args


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
    root: Path,
    empty_project_wheel: Path,
    caplog: pytest.LogCaptureFixture,
    *,
    command: list[str],
    expected_options: tuple[bool, bool],
    expected_cooldowns: tuple[int, int],
) -> None:
    find_links: Final[Path] = root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project_wheel)])
    caplog.clear()

    assert not run_pipx_cli(command)

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
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

    metadata = PipxMetadata(paths.ctx.home / "venvs" / "pycowsay")
    assert (metadata.main_package.pip_args, metadata.injected_packages["empty-project"].pip_args) == (
        ["--no-cache-dir"],
        ["--no-compile"],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_json_stays_pure(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install", "--output", "json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)  # the internal install must not print human text before this
    assert (document["command"], document["status"], captured.err) == (["upgrade"], "success", "")


@skip_if_windows
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
    (paths.ctx.bin_dir / "tool3@1.12").symlink_to(paths.ctx.venvs / "foo-bar-x@1" / "bin" / "tool3.12")

    assert not run_pipx_cli(["upgrade", "foo-bar-x@1"])

    assert sorted(path.name for path in paths.ctx.bin_dir.iterdir()) == ["tool3.12@1"]
