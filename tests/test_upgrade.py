from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING, Final, cast

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    skip_if_windows,
    unwrap_log_text,
)
from package_info import PKG
from pipx import paths
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
    name = "pylint"
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
    assert "empty-project is already at latest version" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "--include-injected", "pylint"])
    captured = capsys.readouterr()
    assert "upgraded package pylint" in captured.out
    assert "upgraded package black" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_no_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "pylint"])
    captured = capsys.readouterr()
    assert "upgraded package pylint" in captured.out
    assert "upgraded package black" not in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_install_missing(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_multiple(capsys: pytest.CaptureFixture[str]) -> None:
    name = "pylint"
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
def test_upgrade_preserves_included_dependency(local_extras_project: Path) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
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
    empty_project: Path,
    caplog: pytest.LogCaptureFixture,
    *,
    command: list[str],
    expected_options: tuple[bool, bool],
    expected_cooldowns: tuple[int, int],
) -> None:
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project)])
    caplog.clear()

    assert not run_pipx_cli(command)

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        "--uploaded-prior-to P7D" in caplog.text,
        "--uploaded-prior-to P5D" in caplog.text,
        (metadata.main_package.cooldown_days, metadata.injected_packages["empty-project"].cooldown_days),
    ) == (*expected_options, expected_cooldowns)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_injected_uses_stored_pip_args(empty_project: Path) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--pip-args=--no-cache-dir"])
    assert not run_pipx_cli(["inject", "pycowsay", str(empty_project), "--pip-args=--no-compile"])

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
