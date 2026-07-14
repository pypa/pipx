from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final
from unittest import mock

import pytest

from helpers import app_name, run_pipx_cli, skip_if_windows, unwrap_log_text
from package_info import PKG
from pipx import paths, shared_libs
from pipx.backends import Backend
from pipx.constants import EXIT_CODE_OK
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture

TEST_DATA_PATH = "./testdata/test_package_specifier"


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--help"])
    captured = capsys.readouterr()
    assert "apps you can run from anywhere" in captured.out


def install_packages(capsys, pipx_temp_env, caplog, packages, package_names=()):
    if len(package_names) != len(packages):
        package_names = packages

    run_pipx_cli(["install", *packages, "--verbose"])
    captured = capsys.readouterr()
    for package_name in package_names:
        assert f"installed package {package_name}" in captured.out
    if not sys.platform.startswith("win"):
        # TODO assert on windows too
        # https://github.com/pypa/pipx/issues/217
        assert "symlink missing or pointing to unexpected location" not in captured.out
    assert "not modifying" not in captured.out
    assert "is not on your PATH environment variable" not in captured.out
    assert "⚠️" not in caplog.text
    assert "WARNING" not in caplog.text


@pytest.mark.parametrize(
    "package_name, package_spec",
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
def test_install_easy_packages(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_install_easy_multiple_packages(capsys, pipx_temp_env, caplog):
    install_packages(
        capsys,
        pipx_temp_env,
        caplog,
        ["pycowsay", PKG["black"]["spec"]],
        ["pycowsay", "black"],
    )


def test_install_multiple_packages_reports_success_before_failure(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_package: Final[str] = "pipx-package-does-not-exist"

    return_code: Final[int] = run_pipx_cli(["install", "pycowsay", missing_package])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        return_code,
        "installed package pycowsay" in captured.out,
        "Error installing pipx-package-does-not-exist" in captured.err,
        (paths.ctx.venvs / "pycowsay").exists(),
        (paths.ctx.venvs / missing_package).exists(),
    ) == (1, True, True, True, False)


@pytest.mark.parametrize(
    "package_name, package_spec",
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
@skip_if_windows
def test_install_easy_packages_globally(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        # ("cloudtoken", PKG["cloudtoken"]["spec"]),
        ("awscli", PKG["awscli"]["spec"]),
        ("ansible", PKG["ansible"]["spec"]),
        ("shell-functools", PKG["shell-functools"]["spec"]),
    ],
)
def test_install_tricky_packages(capsys, pipx_temp_env, caplog, package_name, package_spec):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")
    if sys.platform.startswith("win") and package_name == "ansible":
        pytest.skip("Ansible is not installable on Windows")

    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_install_multiple_packages_when_some_already_installed(capsys, pipx_temp_env, caplog):
    run_pipx_cli(["install", "black", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package black" in captured.out
    assert "installed package pycowsay" in captured.out

    run_pipx_cli(["install", "black", "pycowsay", "isort"])
    captured = capsys.readouterr()
    assert "black" in captured.out and "already seems to be installed" in captured.out
    assert "pycowsay" in captured.out and "already seems to be installed" in captured.out
    assert "installed package isort" in captured.out


def test_install_tricky_multiple_packages(capsys, pipx_temp_env, caplog):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")

    packages = ["awscli", "shell-functools"]  # cloudtoken is temporarily removed
    package_specs = [PKG[package]["spec"] for package in packages]

    install_packages(capsys, pipx_temp_env, caplog, package_specs, packages)


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("pycowsay", "git+https://github.com/cs01/pycowsay.git@master"),
        ("pylint", PKG["pylint"]["spec"]),
        ("nox", "https://github.com/wntrblm/nox/archive/2022.1.7.zip"),
    ],
)
def test_install_package_specs(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_force_install(pipx_temp_env, capsys):
    run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # print(captured.out)
    assert "installed package" in captured.out

    run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package" not in captured.out
    assert "pycowsay" in captured.out and "already seems to be installed" in captured.out

    run_pipx_cli(["install", "pycowsay", "--force"])
    captured = capsys.readouterr()
    assert "Installing to existing venv" in captured.out


def test_force_install_does_not_record_internal_pip_args(pipx_temp_env: None) -> None:
    assert run_pipx_cli(["install", PKG["pycowsay"]["spec"]]) == 0
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--force"]),
        PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.pip_args,
    ) == (0, [])


@pytest.mark.parametrize(
    ("package_name", "display_name", "install_args", "has_dependency_apps"),
    [
        pytest.param(
            "pygdbmi",
            "pygdbmi_test",
            [PKG["pygdbmi"]["spec"], "--suffix=_test"],
            False,
            id="library-with-suffix",
        ),
        pytest.param("jupyter", "jupyter", [PKG["jupyter"]["spec"]], True, id="dependency-apps"),
    ],
)
def test_install_no_apps_guidance(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    package_name: str,
    display_name: str,
    install_args: list[str],
    has_dependency_apps: bool,
) -> None:
    return_code = run_pipx_cli(["install", *install_args])

    error = capsys.readouterr().err
    assert (
        return_code,
        f"No apps associated with package {display_name}" in error,
        f"pipx inject <environment> {package_name}" in error,
        f"--preinstall {package_name}" in error,
        "--include-apps-from PACKAGE" in error,
    ) == (1, True, True, True, has_dependency_apps)


def test_install_records_expected_app(pipx_temp_env: None) -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])

    assert PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.expected_apps == ["pycowsay"]


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
def test_install_from_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    backend: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv is not installed")
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert not run_pipx_cli(["install", "--backend", backend, "--lock", str(lock_file), "pycowsay>=0"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (
        metadata.package_version,
        metadata.lock_file,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
    ) == ("0.0.0.2", lock_file.resolve(), True)


@pytest.mark.parametrize(
    ("backend", "backend_option"),
    [
        pytest.param("pip", "--uploaded-prior-to P7D", id="pip"),
        pytest.param("uv", "--exclude-newer P7D", id="uv"),
    ],
)
def test_install_cooldown(
    pipx_temp_env: None,
    root: Path,
    caplog: pytest.LogCaptureFixture,
    backend: str,
    backend_option: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv is not installed")
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    assert not run_pipx_cli(
        [
            "install",
            "--backend",
            backend,
            "--cooldown",
            "7",
            f"--pip-args=--no-index --find-links={find_links}",
            PKG["pycowsay"]["spec"],
        ]
    )

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (backend_option in caplog.text, metadata.cooldown_days) == (True, 7)


@pytest.mark.parametrize("value", [pytest.param("-1", id="negative"), pytest.param("invalid", id="not-an-integer")])
def test_install_rejects_invalid_cooldown(value: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="2"):
        run_pipx_cli(["install", "--cooldown", value, "pycowsay"])

    assert "--cooldown must be a non-negative integer" in capsys.readouterr().err


@pytest.mark.parametrize("editable", [pytest.param(False, id="wheel"), pytest.param(True, id="editable")])
def test_install_source_from_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    make_project_with_dependency: Callable[[str], Path],
    editable: bool,
) -> None:
    project = make_project_with_dependency("pycowsay==0.0.0.2")
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert not run_pipx_cli(["install", *(["--editable"] if editable else []), "--lock", str(lock_file), str(project)])

    metadata = PipxMetadata(paths.ctx.venvs / "empty-project").main_package
    assert (metadata.package_version, metadata.lock_file, metadata.apps, metadata.pip_args) == (
        "0.1.0",
        lock_file.resolve(),
        [app_name("empty-project")],
        ["--editable"] if editable else [],
    )


def test_install_rejects_incomplete_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    make_project_with_dependency: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = make_project_with_dependency("black==22.8.0")
    lock_file = make_pylock("pycowsay", "0.0.0.2")

    assert run_pipx_cli(["install", "--lock", str(lock_file), str(project)])

    assert (
        "does not satisfy empty-project" in capsys.readouterr().err,
        (paths.ctx.venvs / "empty-project").exists(),
    ) == (True, False)


@pytest.mark.parametrize(
    ("package_spec", "environment", "expected_error"),
    [
        pytest.param("pycowsay==999", "pycowsay", r"does\s+not\s+satisfy\s+pycowsay==999", id="version"),
        pytest.param("black", "black", r"does\s+not\s+contain\s+black", id="package"),
    ],
)
def test_install_rejects_target_outside_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    package_spec: str,
    environment: str,
    expected_error: str,
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")

    assert run_pipx_cli(["install", "--lock", str(lock_file), package_spec])

    error = unwrap_log_text(capsys.readouterr().err)
    assert (
        re.search(expected_error, error) is not None,
        (paths.ctx.venvs / environment).exists(),
    ) == (True, False)


def test_install_rejects_invalid_pylock(
    pipx_temp_env: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = tmp_path / "pylock.toml"
    lock_file.write_text("invalid = true\n", encoding="utf-8")

    assert run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])

    assert (
        "Error installing packages from" in unwrap_log_text(capsys.readouterr().err),
        (paths.ctx.venvs / "pycowsay").exists(),
    ) == (True, False)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["install", "--force", "pycowsay"], id="force"),
        pytest.param(["reinstall", "pycowsay"], id="reinstall"),
    ],
)
def test_install_reapplies_recorded_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    command: list[str],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    marker = paths.ctx.venvs / "pycowsay" / "marker"
    marker.touch()

    assert not run_pipx_cli(command)

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (marker.exists(), metadata.package_version, metadata.lock_file) == (
        False,
        "0.0.0.2",
        lock_file.resolve(),
    )


def test_install_restores_environment_after_pylock_mismatch(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    marker = paths.ctx.venvs / "pycowsay" / "marker"
    marker.touch()

    assert run_pipx_cli(["install", "--force", "--lock", str(lock_file), "pycowsay==999"])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (marker.exists(), metadata.package_version, metadata.lock_file) == (
        True,
        "0.0.0.2",
        lock_file.resolve(),
    )


def test_install_upgrade_skips_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["install", "--upgrade", "pycowsay==999"])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (
        "Not upgrading locked package pycowsay. Update its lock file and run `pipx reinstall pycowsay`."
        in unwrap_log_text(capsys.readouterr().out),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


def test_install_rejects_cooldown_for_recorded_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["install", "--force", "--cooldown", "7", "pycowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (
        "--cooldown cannot modify a locked environment" in unwrap_log_text(capsys.readouterr().err),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


@pytest.mark.parametrize(
    ("package_args", "lock_name", "lock_exists", "expected_error"),
    [
        pytest.param(["pycowsay", "black"], "pylock.test.toml", True, "--lock accepts one package spec", id="packages"),
        pytest.param(
            ["--preinstall", "black", "pycowsay"],
            "pylock.test.toml",
            True,
            "--lock cannot be combined with --preinstall",
            id="preinstall",
        ),
        pytest.param(
            ["--upgrade", "pycowsay"],
            "pylock.test.toml",
            True,
            "--lock cannot be combined with --upgrade",
            id="upgrade",
        ),
        pytest.param(
            ["--cooldown", "7", "pycowsay"],
            "pylock.test.toml",
            True,
            "--lock cannot be combined with --cooldown",
            id="cooldown",
        ),
        pytest.param(["pycowsay"], "lock.toml", True, "Lock files must be named", id="name"),
        pytest.param(["pycowsay"], "pylock.missing.toml", False, "Lock file does not exist", id="missing"),
    ],
)
def test_install_rejects_invalid_pylock_options(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    package_args: list[str],
    lock_name: str,
    lock_exists: bool,
    expected_error: str,
) -> None:
    lock_file = tmp_path / lock_name
    if lock_exists:
        make_pylock("pycowsay", "0.0.0.2").rename(lock_file)

    assert run_pipx_cli(["install", "--lock", str(lock_file), *package_args])

    assert expected_error in unwrap_log_text(capsys.readouterr().err)


@pytest.mark.parametrize(
    ("app_args", "expected_error"),
    [
        pytest.param(["--app", "missing"], "expected app missing", id="one"),
        pytest.param(
            ["--app", "missing", "--app", "absent"],
            "expected apps absent, missing",
            id="multiple",
        ),
    ],
)
def test_install_missing_expected_app_rolls_back(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    app_args: list[str],
    expected_error: str,
) -> None:
    return_code = run_pipx_cli(["install", *app_args, PKG["pycowsay"]["spec"]])

    captured = capsys.readouterr()
    error = " ".join(captured.err.split())
    assert (
        return_code,
        f"Package pycowsay does not provide {expected_error}. Available apps: pycowsay." in error,
        (paths.ctx.venvs / "pycowsay").exists(),
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
    ) == (1, True, False, False)


@pytest.mark.parametrize(
    ("package_spec", "pin"),
    [
        pytest.param("pycowsay>=0", False, id="satisfied"),
        pytest.param("pycowsay==999", True, id="pinned"),
    ],
)
def test_install_upgrade_records_expected_app_without_package_change(
    pipx_temp_env: None,
    package_spec: str,
    pin: bool,
) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    if pin:
        assert not run_pipx_cli(["pin", "pycowsay"])

    assert not run_pipx_cli(["install", "--upgrade", "--app", "pycowsay", package_spec])

    assert PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.expected_apps == ["pycowsay"]


def test_install_accepts_expected_dependency_app(pipx_temp_env: None, root: Path) -> None:
    package = f"{root / TEST_DATA_PATH / 'local_extras'}[cow]"

    assert not run_pipx_cli(["install", "--include-deps", "--app", "pycowsay", package])

    assert PipxMetadata(paths.ctx.venvs / "repeatme").main_package.expected_apps == ["pycowsay"]


def test_install_upgrade_reexposes_expected_dependency_resources(
    pipx_temp_env: None,
    root: Path,
    tmp_path: Path,
) -> None:
    dependency: Final[Path] = root / TEST_DATA_PATH / "local_manpage"
    project: Final[Path] = tmp_path / "expected-dependency-app"
    shutil.copytree(root / "testdata/empty_project", project)
    pyproject: Final[Path] = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'requires-python = ">=3.10"\n',
            f'dependencies = [\n  "local-manpage @ {dependency.as_uri()}",\n]\nrequires-python = ">=3.10"\n',
        ),
        encoding="utf-8",
    )
    assert not run_pipx_cli(["install", "--include-deps", "--app", "local-manpage", str(project)])
    app_path: Final[Path] = paths.ctx.bin_dir / app_name("local-manpage")
    man_path: Final[Path] = paths.ctx.man_dir / "man1/local-manpage.1"
    app_path.unlink()
    man_path.unlink()
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "0.1.0"', 'version = "0.2.0"'),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["install", "--upgrade", str(project)])

    assert (app_path.exists(), man_path.exists()) == (True, True)


def test_install_expected_app_rejects_multiple_specs(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--app", "pycowsay", "pycowsay", PKG["black"]["spec"]])

    assert (
        "--app accepts one package spec" in capsys.readouterr().err,
        (paths.ctx.venvs / "pycowsay").exists(),
        (paths.ctx.venvs / "black").exists(),
    ) == (True, False, False)


def test_install_force_preserves_expected_app(pipx_temp_env: None) -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])

    assert not run_pipx_cli(["install", "--force", PKG["pycowsay"]["spec"]])

    assert (
        PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.expected_apps,
        tuple(paths.ctx.venvs.glob(".pycowsay-*-pipx-backup")),
    ) == (["pycowsay"], ())


def test_install_backup_failure_preserves_existing_environment(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])
    mocker.patch("pipx.commands.transaction.copytree", autospec=True, side_effect=OSError("disk full"))

    assert run_pipx_cli(["install", "--force", PKG["pycowsay"]["spec"]])

    assert (
        "pipx could not back up environment pycowsay: disk full" in capsys.readouterr().err,
        PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.expected_apps,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
    ) == (True, ["pycowsay"], True)


@pytest.mark.parametrize(
    "reconciliation",
    [
        pytest.param("force", id="install-force"),
        pytest.param("install-upgrade", id="install-upgrade"),
        pytest.param("upgrade", id="upgrade"),
        pytest.param("reinstall", id="reinstall"),
    ],
)
def test_install_missing_recorded_app_restores_existing_environment(
    missing_expected_app_project: Path,
    capsys: pytest.CaptureFixture[str],
    reconciliation: str,
) -> None:
    commands = {
        "force": ["install", "--force", str(missing_expected_app_project)],
        "install-upgrade": ["install", "--upgrade", str(missing_expected_app_project)],
        "upgrade": ["upgrade", "empty-project"],
        "reinstall": ["reinstall", "empty-project"],
    }
    assert run_pipx_cli(commands[reconciliation])

    captured = capsys.readouterr()
    metadata = PipxMetadata(paths.ctx.venvs / "empty-project").main_package
    error = " ".join(captured.err.split())
    assert (
        "Package empty-project does not provide expected app empty-project. Available apps: none." in error,
        metadata.package_version,
        metadata.expected_apps,
        metadata.apps,
        (paths.ctx.bin_dir / app_name("empty-project")).exists(),
    ) == (True, "0.1.0", ["empty-project"], [app_name("empty-project")], True)


@pytest.fixture
def missing_expected_app_project(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    root: Path,
    tmp_path: Path,
) -> Path:
    project = tmp_path / "expected-app-project"
    shutil.copytree(root / "testdata/empty_project", project)
    assert not run_pipx_cli(["install", "--app", "empty-project", str(project)])
    capsys.readouterr()

    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text()
        .replace('version = "0.1.0"', 'version = "0.2.0"')
        .replace('scripts.empty-project = "empty_project.main:cli"\n', "")
        .replace('entry-points."pipx.run".empty-project = "empty_project.main:cli"\n', "")
    )
    return project


def test_install_same_package_twice_no_force(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "already seems to be installed" in captured.out
    assert "pipx upgrade" in captured.out
    assert "0.0.0.2" in captured.out


def test_install_upgrade_installs_missing_package(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--upgrade", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert "installed package black 22.8.0" in captured.out


def test_install_upgrade_reconciles_package_spec(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])

    assert not run_pipx_cli(["install", "--upgrade", "--upgrade-strategy=eager", "black==22.10.0"])
    captured = capsys.readouterr()
    assert "upgraded package black from 22.8.0 to 22.10.0" in captured.out
    metadata = PipxMetadata(paths.ctx.venvs / "black").main_package
    assert metadata.package_version == "22.10.0"
    assert metadata.pip_args == []

    assert not run_pipx_cli(["install", "--upgrade", "black<22.9"])
    captured = capsys.readouterr()
    assert "upgraded package black from 22.10.0 to 22.8.0" in captured.out
    assert PipxMetadata(paths.ctx.venvs / "black").main_package.package_version == "22.8.0"


def test_install_upgrade_multiple_existing(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    package_specs = [PKG["black"]["spec"], PKG["pycowsay"]["spec"]]
    assert run_pipx_cli(["install", *package_specs]) == EXIT_CODE_OK
    capsys.readouterr()

    assert run_pipx_cli(["install", "--upgrade", *package_specs]) == EXIT_CODE_OK
    output = capsys.readouterr().out
    assert ("black 22.8.0 already satisfies" in output, "pycowsay 0.0.0.2 already satisfies" in output) == (
        True,
        True,
    )


def test_install_reuses_empty_environment_dir(pipx_temp_env: None) -> None:
    (paths.ctx.venvs / "pycowsay").mkdir(parents=True)
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"]]),
        PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.package,
    ) == (EXIT_CODE_OK, "pycowsay")


def test_install_upgrade_satisfied_spec_is_offline(pipx_temp_env, capsys, mocker: MockerFixture):
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    check_shared = mocker.patch.object(Venv, "check_upgrade_shared_libs", autospec=True)
    upgrade_package = mocker.patch.object(Venv, "upgrade_package", autospec=True)

    assert not run_pipx_cli(["install", "--upgrade", "black>=22,<23"])
    captured = capsys.readouterr()
    assert "black 22.8.0 already satisfies black>=22,<23" in captured.out
    check_shared.assert_not_called()
    upgrade_package.assert_not_called()


def test_install_upgrade_strategy_requires_upgrade(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", "--upgrade-strategy=eager", PKG["black"]["spec"]])
    assert "--upgrade-strategy requires --upgrade" in capsys.readouterr().err


def test_install_existing_package_skips_shared_lib_maintenance(pipx_temp_env: None, mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", PKG["pycowsay"]["spec"]]) == 0
    mocker.patch.object(shared_libs.shared_libs, "has_been_updated_this_run", False)
    mocker.patch(
        "pipx.shared_libs.time.time",
        return_value=shared_libs.shared_libs.pip_path.stat().st_mtime + shared_libs.SHARED_LIBS_MAX_AGE_SEC + 1,
    )
    run_subprocess = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ModuleSpec", stderr=""),
    )

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])

    run_subprocess.assert_not_called()


def test_include_deps(pipx_temp_env: None) -> None:
    assert not run_pipx_cli(["install", PKG["jupyter"]["spec"], "--include-deps"])


def test_install_include_apps_from_dependency(
    pipx_temp_env: None,
    local_extras_project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"

    assert not run_pipx_cli(["install", package, "--include-apps-from", "PyCowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_apps_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
        (paths.ctx.man_dir / "man6" / "pycowsay.6").exists(),
    ) == (["pycowsay"], True, False, True)
    capsys.readouterr()
    assert not run_pipx_cli(["list"])
    output: Final[str] = capsys.readouterr().out
    assert (f"    - {app_name('pycowsay')}" in output, f"    - {app_name('black')}" in output) == (True, False)


def test_install_force_replaces_included_dependency_resources(
    pipx_temp_env: None,
    local_extras_project: Path,
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", package, "--include-apps-from", "pycowsay"])

    assert not run_pipx_cli(["install", "--force", package, "--include-apps-from", "black"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_apps_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.man_dir / "man6" / "pycowsay.6").exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["black"], False, False, True)


def test_install_include_apps_from_missing_dependency_rolls_back(
    pipx_temp_env: None,
    local_extras_project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package: Final[str] = f"{local_extras_project}[cow]"

    assert run_pipx_cli(["install", package, "--include-apps-from", "black"])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        "Cannot expose apps from black for package repeatme. Dependencies with apps or manual pages: pycowsay." in error
    )
    assert not (paths.ctx.venvs / "repeatme").exists()


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("zest-releaser", PKG["zest-releaser"]["spec"]),
        ("tox-ini-fmt", PKG["tox-ini-fmt"]["spec"]),
    ],
)
def test_name_tricky_characters(caplog, capsys, pipx_temp_env, package_name, package_spec):
    if sys.platform == "darwin" and package_name == "zest-releaser":
        pytest.skip("Skipping zest-releaser due to missing Python 3.13 wheel for cmarkgfm on macOS")

    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_extra(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "nox[tox_to_nox]==2023.4.22", "--include-deps"])
    captured = capsys.readouterr()
    assert f"- {app_name('tox')}\n" in captured.out


def test_install_local_extra(pipx_temp_env, capsys, monkeypatch, root):
    assert not run_pipx_cli(["install", str(root / f"{TEST_DATA_PATH}/local_extras[cow]"), "--include-deps"])
    captured = capsys.readouterr()
    assert f"- {app_name('pycowsay')}\n" in captured.out
    assert f"- {Path('man6/pycowsay.6')}\n" in captured.out


def test_path_warning(pipx_temp_env, capsys, monkeypatch, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "is not on your PATH environment variable" not in unwrap_log_text(caplog.text)

    monkeypatch.setenv("PATH", "")
    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    assert "is not on your PATH environment variable" in unwrap_log_text(caplog.text)


@skip_if_windows
def test_existing_symlink_points_to_existing_wrong_location_warning(pipx_temp_env, caplog, capsys):
    paths.ctx.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.ctx.bin_dir / "pycowsay").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in unwrap_log_text(caplog.text)
    assert "symlink missing or pointing to unexpected location" in captured.out
    # bin dir was on path, so the warning should NOT appear (even though the symlink
    # pointed to the wrong location)
    assert "is not on your PATH environment variable" not in captured.err


@skip_if_windows
def test_existing_man_page_symlink_points_to_existing_wrong_location_warning(pipx_temp_env, caplog, capsys):
    (paths.ctx.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.ctx.man_dir / "man6" / "pycowsay.6").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in unwrap_log_text(caplog.text)
    assert "symlink missing or pointing to unexpected location" in captured.out


@skip_if_windows
def test_existing_symlink_points_to_nothing(pipx_temp_env, capsys):
    paths.ctx.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.ctx.bin_dir / "pycowsay").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


@skip_if_windows
def test_existing_man_page_symlink_points_to_nothing(pipx_temp_env, capsys):
    (paths.ctx.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.ctx.man_dir / "man6" / "pycowsay.6").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


def test_pip_args_forwarded_to_shared_libs(pipx_ultra_temp_env, capsys, caplog):
    # strategy:
    # 1. start from an empty env to ensure the next command would trigger a shared lib update
    assert shared_libs.shared_libs.needs_upgrade
    # 2. install any package with --no-index
    # and check that the shared library update phase fails
    return_code = run_pipx_cli(["install", "--verbose", "--pip-args=--no-index", "pycowsay"])
    assert "Upgrading shared libraries in" in caplog.text

    captured = capsys.readouterr()
    assert return_code != 0
    assert "ERROR: Could not find a version that satisfies the requirement pip" in captured.err
    assert "Failed to upgrade shared libraries" in caplog.text


def test_pip_args_forwarded_to_package_name_determination(pipx_temp_env, capsys):
    assert run_pipx_cli(
        [
            "install",
            # use a valid spec and invalid pip args
            "https://github.com/psf/black/archive/22.8.0.zip",
            "--verbose",
            "--pip-args='--asdf'",
        ]
    )
    captured = capsys.readouterr()
    assert "--asdf" in captured.err
    assert "Cannot determine package name from spec" not in captured.err


def test_package_name_determination_preserves_install_error(mocker: MockerFixture) -> None:
    venv: Final[Venv] = Venv(Path("requires-newer-python-venv"))
    backend: Final[MagicMock] = mocker.create_autospec(Backend, instance=True)
    backend.cooldown_args.return_value = []
    backend.install.return_value = subprocess.CompletedProcess(
        ["pip", "install", "requires-newer-python"],
        1,
        stdout="",
        stderr="ERROR: Package 'requires-newer-python' requires a different Python\n",
    )
    mocker.patch.object(venv, "_backend", backend)
    mocker.patch.object(venv, "list_installed_packages", return_value=set())

    with pytest.raises(PipxError) as excinfo:
        venv.install_package_no_deps("requires-newer-python", [])

    error: Final[str] = str(excinfo.value)
    assert "requires a different Python" in error
    assert "Cannot determine package name from spec" not in error


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows only")
def test_pip_args_with_windows_path(pipx_temp_env, capsys):

    assert run_pipx_cli(
        [
            "install",
            "pycowsay",
            "--verbose",
            "--pip-args='--no-index --find-links=D:\\TEST\\DIR'",
        ]
    )
    captured = capsys.readouterr()
    assert r"D:\\TEST\\DIR" in captured.err


@pytest.mark.parametrize("constraint_flag", ["-c ", "--constraint ", "--constraint="])
def test_pip_args_with_constraint_relative_path(constraint_flag, pipx_temp_env, tmp_path, caplog):
    constraint_file_name = "constraints.txt"
    package_name = "ipython"
    package_version = "8.23.0"

    os.chdir(tmp_path)
    constraints_file = tmp_path / constraint_file_name
    constraints_file.write_text(f"{package_name}!={package_version}")
    constraints_file.touch()

    assert not run_pipx_cli(["install", f"--pip-args='{constraint_flag}{constraint_file_name}'", package_name])

    assert f"{constraint_flag}{constraints_file}" in caplog.text

    subprocess_package_version = subprocess.run([package_name, "--version"], capture_output=True, text=True, check=False)
    subprocess_package_version_output = subprocess_package_version.stdout.strip()
    assert subprocess_package_version_output != package_version


def test_pip_args_with_attached_constraint_records_absolute_path(
    pipx_temp_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constraint_file = tmp_path / "constraints.txt"
    constraint_file.write_text("pycowsay==0.0.0.2")
    monkeypatch.chdir(tmp_path)

    assert (
        run_pipx_cli(["install", "--pip-args=-cconstraints.txt", PKG["pycowsay"]["spec"]]),
        PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.pip_args[:1],
    ) == (0, [f"-c{constraint_file}"])


@pytest.mark.parametrize("constraint_flag", ["-c ", "--constraint ", "--constraint="])
def test_pip_args_with_wrong_constraint_fail(constraint_flag, pipx_ultra_temp_env, tmp_path, capsys):
    constraint_file_name = "constraints.txt"
    os.chdir(tmp_path)

    assert run_pipx_cli(["install", f"--pip-args='{constraint_flag}{constraint_file_name}'", "pycowsay"])

    # pip phrases this as "requirements file" (<26) or "constraint file" (>=26), so match the common part
    assert f"[Errno 2] No such file or directory: '{constraint_file_name}'" in capsys.readouterr().err


def test_install_suffix(pipx_temp_env, capsys):
    name = "pbr"

    suffix = "_a"
    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_a = app_name(f"{name}{suffix}")
    assert f"- {name_a}" in captured.out

    suffix = "_b"
    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_b = app_name(f"{name}{suffix}")
    assert f"- {name_b}" in captured.out

    assert (paths.ctx.bin_dir / name_a).exists()
    assert (paths.ctx.bin_dir / name_b).exists()


def test_man_page_install(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert f"- {Path('man6/pycowsay.6')}" in captured.out
    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").exists()


def test_editable_install_links_man_pages(pipx_temp_env, capsys, root):
    package = (root / TEST_DATA_PATH / "local_manpage").as_posix()

    assert not run_pipx_cli(["install", "--editable", package])
    captured = capsys.readouterr()

    assert f"- {app_name('local-manpage')}\n" in captured.out
    assert f"- {Path('man1/local-manpage.1')}" in captured.out
    assert (paths.ctx.venvs / "local-manpage" / "share" / "man" / "man1" / "local-manpage.1").exists()
    assert (paths.ctx.man_dir / "man1" / "local-manpage.1").exists()

    assert not run_pipx_cli(["uninstall", "local-manpage"])
    assert not (paths.ctx.man_dir / "man1" / "local-manpage.1").exists()


def test_install_pip_failure(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", "weblate==4.3.1", "--verbose"])
    captured = capsys.readouterr()

    assert "Fatal error from pip" in captured.err

    pip_log_file_match = re.search(r"Full pip output in file:\s+(\S.+)$", captured.err, re.MULTILINE)
    assert pip_log_file_match
    assert Path(pip_log_file_match[1]).exists()

    assert re.search(r"pip (failed|seemed to fail) to build package", captured.err)


def test_install_local_archive(pipx_temp_env, monkeypatch, capsys, root):
    monkeypatch.chdir(root / TEST_DATA_PATH / "local_extras")

    subprocess.run([sys.executable, "-m", "pip", "wheel", "."], check=True)
    assert not run_pipx_cli(["install", "repeatme-0.1-py3-none-any.whl"])
    captured = capsys.readouterr()
    assert f"- {app_name('repeatme')}\n" in captured.out


def test_force_install_changes(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "https://github.com/wntrblm/nox/archive/2022.1.7.zip"])
    captured = capsys.readouterr()
    assert "2022.1.7" in captured.out

    assert not run_pipx_cli(["install", "nox", "--force"])
    captured = capsys.readouterr()
    assert "2022.1.7" not in captured.out


def test_force_install_changes_editable(pipx_temp_env, root, capsys):
    empty_project_path_as_string = (root / "testdata" / "empty_project").as_posix()
    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string])
    captured = capsys.readouterr()
    assert "empty-project" in captured.out

    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string, "--force"])
    captured = capsys.readouterr()
    assert "Installing to existing venv 'empty-project'" in captured.out


def test_install_multiple_packages_preserves_editable_for_local_package(pipx_temp_env: None, root: Path) -> None:
    local_package = (root / "testdata" / "empty_project").as_posix()
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"], local_package, "--editable"]),
        PipxMetadata(paths.ctx.venvs / "empty-project").main_package.pip_args,
    ) == (0, ["--editable"])


def test_preinstall(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "black", "nox"])
    assert "black" in caplog.text


def test_preinstall_cooldown(
    pipx_temp_env: None,
    root: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    assert not run_pipx_cli(
        [
            "install",
            "--preinstall",
            PKG["black"]["spec"],
            "--cooldown",
            "7",
            f"--pip-args=--no-index --find-links={find_links}",
            PKG["nox"]["spec"],
        ]
    )

    assert (
        caplog.text.count("--uploaded-prior-to P7D"),
        PipxMetadata(paths.ctx.venvs / "nox").main_package.cooldown_days,
    ) == (2, 7)


def test_preinstall_multiple(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "chardet", "--preinstall", "colorama", "nox"])
    assert "chardet" in caplog.text
    assert "colorama" in caplog.text


def test_preinstall_specific_version(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "black==22.8.0", "nox"])
    assert "black==22.8.0" in caplog.text


@pytest.mark.xfail
def test_do_not_wait_for_input(pipx_temp_env, pipx_session_shared_dir, monkeypatch):
    monkeypatch.setenv("PIP_INDEX_URL", "http://127.0.0.1:8080/simple")
    run_pipx_cli(["install", "pycowsay"])


def test_passed_python_and_force_flag_warning(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["install", "--python", sys.executable, "--force", "black"])
    captured = capsys.readouterr()
    assert "--python is ignored when --force is passed." in captured.out

    assert not run_pipx_cli(["install", "black", "--force"])
    captured = capsys.readouterr()
    assert "--python is ignored when --force is passed." not in captured.out, (
        "Should only print warning if both flags present"
    )

    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    captured = capsys.readouterr()
    assert "--python is ignored when --force is passed." not in captured.out, (
        "Should not print warning if package does not exist yet"
    )


@pytest.mark.parametrize(
    ("python_version", "fetch_flag", "expect_deprecation"),
    [
        pytest.param("3.0", "--fetch-python=missing", False, id="3.0-fetch-python-missing"),
        pytest.param("3.1", "--fetch-python=missing", False, id="3.1-fetch-python-missing"),
        pytest.param("3.0", "--fetch-missing-python", True, id="3.0-deprecated-flag"),
    ],
)
def test_install_fetch_missing_python_invalid(capsys, python_version, fetch_flag, expect_deprecation):
    assert run_pipx_cli(["install", "--python", python_version, fetch_flag, "pycowsay"])
    captured = capsys.readouterr()
    assert f"No executable for the provided Python version '{python_version}' found" in captured.out
    assert ("--fetch-missing-python is deprecated" in captured.err) is expect_deprecation


def test_install_run_in_separate_directory(caplog, capsys, pipx_temp_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    f = Path("argparse.py")
    f.touch()

    install_packages(capsys, pipx_temp_env, caplog, ["pycowsay"], ["pycowsay"])


@skip_if_windows
@pytest.mark.parametrize(
    "python_version",
    [
        str(sys.version_info.major),
        f"{sys.version_info.major}.{sys.version_info.minor}",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ],
)
def test_install_python_command_version(pipx_temp_env, monkeypatch, capsys, python_version):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert python_version in captured.out


@skip_if_windows
def test_install_python_command_version_invalid(pipx_temp_env, capsys):
    python_version = "3.x"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Invalid Python version: {python_version}" in captured.err


@skip_if_windows
def test_install_python_command_version_unsupported(pipx_temp_env, capsys):
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.dev"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Unsupported Python version: {python_version}" in captured.err


@skip_if_windows
def test_install_python_command_version_missing(pipx_temp_env, monkeypatch, capsys):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    python_version = f"{sys.version_info.major + 99}.{sys.version_info.minor}"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Command `python{python_version}` was not found" in captured.err


@skip_if_windows
def test_install_python_command_version_micro_mismatch(pipx_temp_env, monkeypatch, capsys):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro + 1}"
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"It may not match the specified version {python_version} at the micro/patch level" in captured.err


@skip_if_windows
def test_global_flag_before_subcommand_rejected(pipx_temp_env, capsys):
    with pytest.raises(SystemExit) as exc_info:
        run_pipx_cli(["--global", "install", "pycowsay"])
    assert exc_info.value.code == 2, "argparse error should exit with code 2"
    captured = capsys.readouterr()
    assert "unrecognized arguments: --global" in captured.err


def test_install_quiet_flag(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--quiet", "--quiet", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package" not in captured.out
    assert "These apps are now" not in captured.out
    assert "done!" not in captured.out
    assert "done!" not in captured.err


def test_install_json(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": "install",
        "data": {
            "failures": [],
            "packages": [
                {
                    "environment": "pycowsay",
                    "location": str(paths.ctx.venvs / "pycowsay"),
                    "package": "pycowsay",
                    "version": "0.0.0.2",
                }
            ],
            "skipped": [],
        },
        "pipx_result_version": "0.1",
        "status": "success",
    }


def test_install_json_reports_existing(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": "install",
        "data": {
            "failures": [],
            "packages": [],
            "skipped": [
                {
                    "environment": "pycowsay",
                    "package": "pycowsay",
                    "reason": "already-installed",
                }
            ],
        },
        "pipx_result_version": "0.1",
        "status": "success",
    }


def test_install_json_reports_invalid_option(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--upgrade-strategy", "eager", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": "install",
        "data": {
            "failures": [
                {
                    "environment": "pycowsay",
                    "error": "--upgrade-strategy requires --upgrade",
                }
            ],
            "packages": [],
            "skipped": [],
        },
        "pipx_result_version": "0.1",
        "status": "error",
    }


def test_install_json_attributes_name_resolution_failure(
    pipx_temp_env: None,
    empty_project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing: Final[Path] = tmp_path / "missing.whl"

    assert run_pipx_cli(["install", "--output", "json", str(empty_project), str(missing)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out)["data"]["failures"][0]["environment"] == str(missing)


def test_install_json_reports_missing_app(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--app", "missing", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert (
        json.loads(captured.out),
        (paths.ctx.venvs / "pycowsay").exists(),
    ) == (
        {
            "command": "install",
            "data": {
                "failures": [
                    {
                        "environment": "pycowsay",
                        "error": "Package pycowsay does not provide expected app missing. Available apps:\npycowsay.",
                    }
                ],
                "packages": [],
                "skipped": [],
            },
            "pipx_result_version": "0.1",
            "status": "error",
        },
        False,
    )


def test_install_json_reports_existing_upgrade_failure(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "--suffix=-x", "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["install", "--output", "json", "--upgrade", "--app", "missing", "--suffix=-x", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out)["data"]["failures"] == [
        {
            "environment": "pycowsay-x",
            "error": "Package pycowsay does not provide expected app missing. Available apps:\npycowsay.",
        }
    ]


def test_install_keyboard_interrupt_removes_environment(pipx_temp_env: None, mocker: MockerFixture) -> None:
    mocker.patch.object(Venv, "install_package", autospec=True, side_effect=KeyboardInterrupt)

    assert (
        run_pipx_cli(["install", "pycowsay"]),
        (paths.ctx.venvs / "pycowsay").exists(),
    ) == (1, False)


def test_install_error_removes_environment(pipx_temp_env: None, mocker: MockerFixture) -> None:
    mocker.patch.object(Venv, "install_package", autospec=True, side_effect=RuntimeError("failed"))

    with pytest.raises(RuntimeError, match="failed"):
        run_pipx_cli(["install", "pycowsay"])
    assert not (paths.ctx.venvs / "pycowsay").exists()


def test_install_skip_maintenance_without_index(
    pipx_ultra_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    root: Path,
    tmp_path: Path,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheel = shutil.copy2(
        next(
            (root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}").glob(
                "pycowsay-*.whl"
            )
        ),
        wheelhouse,
    )

    assert not run_pipx_cli(
        ["install", "--skip-maintenance", str(wheel), f"--pip-args=--no-index --find-links={wheelhouse}"]
    )

    assert "installed package pycowsay" in capsys.readouterr().out
    assert not shared_libs.shared_libs_auto_upgrade_disabled()
