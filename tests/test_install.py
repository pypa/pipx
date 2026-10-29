from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingTCPServer
from typing import TYPE_CHECKING, Final

import pytest

from helpers import (
    SKIP_IF_WINDOWS,
    MakePylock,
    app_name,
    current_log_file,
    drop_extra_app,
    run_pipx_cli,
    unwrap_log_text,
)
from package_info import PKG
from pipx import main, paths, shared_libs
from pipx.constants import EXIT_CODE_OK
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, PipxMetadata
from pipx.util import redact_url_credentials
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


def test_help_text(capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "exit", side_effect=ValueError("raised in test to exit early"))
    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--help"])
    assert "apps you can run from anywhere" in capsys.readouterr().out


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_wheel_from_file_url(dotted_app_wheel: Path, tmp_path: Path, backend: str) -> None:
    wheel_dir: Final[Path] = tmp_path / "wheels with spaces"
    wheel_dir.mkdir()
    package_spec: Final[str] = dotted_app_wheel.rename(wheel_dir / dotted_app_wheel.name).as_uri()

    assert not run_pipx_cli(["install", "--backend", backend, package_spec])

    assert (
        PipxMetadata(paths.CTX.venvs / "foo-bar-x").main_package.package_or_url,
        (paths.CTX.bin_dir / app_name("tool3.12")).is_file(),
    ) == (package_spec, True)


@pytest.mark.parametrize(
    ("package_name", "package_spec"),
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_easy_packages(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    package_name: str,
    package_spec: str,
) -> None:
    install_packages(capsys, caplog, [package_spec], [package_name])


def install_packages(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    packages: list[str],
    package_names: Sequence[str],
) -> None:
    run_pipx_cli(["install", *packages, "--verbose"])
    out: Final[str] = capsys.readouterr().out
    assert (
        [f"installed package {package_name}" in out for package_name in package_names],
        # https://github.com/pypa/pipx/issues/217 tracks checking this warning on Windows too
        "symlink missing or pointing to unexpected location" in out and not sys.platform.startswith("win"),
        "not modifying" in out,
        "is not on your PATH environment variable" in out,
        "⚠️" in caplog.text,
        "WARNING" in caplog.text,
    ) == ([True] * len(package_names), False, False, False, False, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_easy_multiple_packages(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    install_packages(
        capsys,
        caplog,
        ["pycowsay", PKG["black"]["spec"]],
        ["pycowsay", "black"],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_multiple_packages_reports_success_before_failure(capsys: pytest.CaptureFixture[str]) -> None:
    missing_package: Final[str] = "pipx-package-does-not-exist"

    return_code: Final[int] = run_pipx_cli(["install", "pycowsay", missing_package])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        return_code,
        "installed package pycowsay" in captured.out,
        "Error installing pipx-package-does-not-exist" in captured.err,
        (paths.CTX.venvs / "pycowsay").exists(),
        (paths.CTX.venvs / missing_package).exists(),
    ) == (1, True, True, True, False)


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("/../../owned", id="parent-escape"),
        pytest.param("nested/name", id="separator"),
        pytest.param("has space", id="whitespace"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_unsafe_suffix(capsys: pytest.CaptureFixture[str], suffix: str) -> None:
    return_code: Final[int] = run_pipx_cli(["install", "--suffix", suffix, "pycowsay"])

    assert (return_code, "Invalid suffix" in capsys.readouterr().err, (paths.CTX.venvs / "pycowsay").exists()) == (
        1,
        True,
        False,
    )


@pytest.mark.parametrize(
    ("package_name", "package_spec"),
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_easy_packages_globally(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    package_name: str,
    package_spec: str,
) -> None:
    install_packages(capsys, caplog, [package_spec], [package_name])


@pytest.mark.skipif(bool(os.getenv("FAST")), reason="skipping slow tests")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_tricky_packages(capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    install_packages(capsys, caplog, [PKG["shell-functools"]["spec"]], ["shell-functools"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_multiple_packages_when_some_already_installed(capsys: pytest.CaptureFixture[str]) -> None:
    run_pipx_cli(["install", "black", "pycowsay"])
    first: Final[str] = capsys.readouterr().out
    assert ("installed package black" in first, "installed package pycowsay" in first) == (True, True)

    run_pipx_cli(["install", "black", "pycowsay", "isort"])

    second: Final[str] = capsys.readouterr().out
    assert (
        "black" in second,
        "pycowsay" in second,
        "already seems to be installed" in second,
        "installed package isort" in second,
    ) == (True, True, True, True)


@pytest.mark.skipif(bool(os.getenv("FAST")), reason="skipping slow tests")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_tricky_multiple_packages(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    packages: Final[list[str]] = ["pycowsay", "shell-functools"]

    install_packages(capsys, caplog, [PKG[package]["spec"] for package in packages], packages)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_package_spec_pinned(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    install_packages(capsys, caplog, [PKG["isort"]["spec"]], ["isort"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_package_spec_vcs_url(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    empty_project: Path,
) -> None:
    install_packages(capsys, caplog, [_local_git_spec(empty_project)], ["empty-project"])


def _local_git_spec(project: Path) -> str:
    git: Final[str | None] = shutil.which("git")
    assert git is not None
    config: Final[list[str]] = ["-c", "user.name=pipx tests", "-c", "user.email=pipx@example.invalid"]
    for command in (
        ["init", "--quiet"],
        ["add", "."],
        [*config, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "test fixture"],
    ):
        subprocess.run([git, *command], cwd=project, check=True)
    return f"git+{project.as_uri()}"


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_package_spec_archive_url(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    empty_project: Path,
) -> None:
    with _served_archive_spec(empty_project) as package_spec:
        install_packages(capsys, caplog, [package_spec], ["empty-project"])


@contextmanager
def _served_archive_spec(project: Path) -> Generator[str, None, None]:
    archive: Final[Path] = Path(
        shutil.make_archive(str(project.parent / "empty-project-0.1.0"), "zip", project.parent, project.name)
    )
    handler: Final = partial(SimpleHTTPRequestHandler, directory=str(project.parent))
    # not http.server.HTTPServer: its bind resolves the host name, which stalls for 30 s on macOS CI runners
    with ThreadingTCPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}/{archive.name}"
        finally:
            server.shutdown()


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install(capsys: pytest.CaptureFixture[str]) -> None:
    run_pipx_cli(["install", "pycowsay"])
    assert "installed package" in capsys.readouterr().out
    run_pipx_cli(["install", "pycowsay"])
    skipped: Final[str] = capsys.readouterr().out
    assert (
        "installed package" in skipped,
        "pycowsay" in skipped,
        "already seems to be installed" in skipped,
    ) == (False, True, True)

    run_pipx_cli(["install", "pycowsay", "--force"])

    assert "Installing to existing venv" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install_does_not_record_internal_pip_args() -> None:
    assert run_pipx_cli(["install", PKG["pycowsay"]["spec"]]) == 0
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--force"]),
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args,
    ) == (0, [])


@pytest.mark.parametrize(
    ("pip_args", "recorded"),
    [
        pytest.param("-r requirements.txt", [], id="requirement"),
        pytest.param("--requirement=requirements.txt", [], id="requirement-equals"),
        pytest.param("-rrequirements.txt", [], id="requirement-attached"),
        pytest.param("-qr requirements.txt", ["-q"], id="requirement-clustered"),
        pytest.param("--log pip.log", [], id="log"),
        pytest.param("--log-f pip.log", [], id="log-abbreviated"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_does_not_record_one_shot_pip_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pip_args: str, recorded: list[str]
) -> None:
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["install", "--backend", "pip", f"--pip-args=--no-cache-dir {pip_args}", "pycowsay"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == ["--no-cache-dir", *recorded]


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_applies_one_shot_pip_args_to_its_own_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["install", "--backend", "pip", "--pip-args=--log pip.log", "pycowsay"])

    assert (tmp_path / "pip.log").stat().st_size


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_failed_force_install_keeps_recorded_metadata(
    dotted_app_wheel: Path, make_wheel: Callable[[dict[str, str]], Path], backend: str
) -> None:
    assert not run_pipx_cli(["install", "--backend", backend, str(dotted_app_wheel)])
    metadata_path: Final[Path] = paths.CTX.venvs / "foo-bar-x" / PIPX_INFO_FILENAME
    recorded: Final[str] = metadata_path.read_text(encoding="utf-8")
    # data files unpack into the venv root before the installer writes INSTALLER, here a directory, and fails
    make_wheel({
        "foo_bar_x-1.data/data/pipx_metadata.json": "{}",
        "foo_bar_x-1.dist-info/INSTALLER/placeholder": "",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })

    assert (
        run_pipx_cli(["install", "--force", str(dotted_app_wheel)]),
        metadata_path.read_text(encoding="utf-8"),
    ) == (1, recorded)


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
        pytest.param("requests", "requests", ["requests==2.31.0"], True, id="dependency-apps"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_no_apps_guidance(
    capsys: pytest.CaptureFixture[str],
    package_name: str,
    display_name: str,
    install_args: list[str],
    has_dependency_apps: bool,
) -> None:
    return_code: Final[int] = run_pipx_cli(["install", *install_args])

    # pipx wraps the message to the terminal width, which can split any of the phrases below across lines
    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        return_code,
        f"No apps associated with package {display_name}" in error,
        f"pipx inject <environment> {package_name}" in error,
        f"--preinstall {package_name}" in error,
        "--include-resources-from PACKAGE" in error,
    ) == (1, True, True, True, has_dependency_apps)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_records_expected_app() -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.expected_apps == ["pycowsay"]


# the grouped row mirrors a `pipx manifest lock` output: nab gates every package on the tool's group and the lock
# names that group as its default
@pytest.mark.parametrize("group", [pytest.param(None, id="flat"), pytest.param("pycowsay", id="grouped")])
@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param("uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_from_pylock(make_pylock: MakePylock, backend: str, group: str | None) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2", group)

    assert not run_pipx_cli(["install", "--backend", backend, "--lock", str(lock_file), "pycowsay>=0"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (
        metadata.package_version,
        metadata.lock_file,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
    ) == ("0.0.0.2", lock_file.resolve(), True)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.parametrize(
    ("recorded", "other"), [pytest.param("pip", "uv", id="pip"), pytest.param("uv", "pip", id="uv")]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_force_pylock_keeps_the_recorded_backend(make_pylock: MakePylock, recorded: str, other: str) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2", None)
    assert not run_pipx_cli(["install", "--backend", recorded, PKG["pycowsay"]["spec"]])

    assert not run_pipx_cli(["install", "--force", "--backend", other, "--lock", str(lock_file), "pycowsay>=0"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (metadata.backend, metadata.main_package.lock_file) == (recorded, lock_file.resolve())


@pytest.mark.parametrize(
    ("backend", "backend_option"),
    [
        pytest.param("pip", "--uploaded-prior-to P7D", id="pip"),
        pytest.param(
            "uv",
            "--exclude-newer P7D",
            id="uv",
            marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed"),
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_cooldown(
    package_cache_dir: Path, caplog: pytest.LogCaptureFixture, backend: str, backend_option: str
) -> None:
    assert not run_pipx_cli([
        "install",
        "--backend",
        backend,
        "--cooldown",
        "7",
        f"--pip-args=--no-index --find-links={package_cache_dir}",
        PKG["pycowsay"]["spec"],
    ])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (backend_option in caplog.text, metadata.cooldown_days) == (True, 7)


@pytest.mark.parametrize(
    ("cli_args", "expected_days"),
    [
        pytest.param([], 7, id="env"),
        pytest.param(["--cooldown", "3"], 3, id="flag-wins"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_env_cooldown(
    package_cache_dir: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cli_args: list[str],
    expected_days: int,
) -> None:
    monkeypatch.setattr(main, "COOLDOWN", 7)

    assert not run_pipx_cli([
        "install",
        "--backend",
        "pip",
        *cli_args,
        f"--pip-args=--no-index --find-links={package_cache_dir}",
        PKG["pycowsay"]["spec"],
    ])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (f"--uploaded-prior-to P{expected_days}D" in caplog.text, metadata.cooldown_days) == (True, expected_days)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_env_cooldown_opted_out_by_flag(
    package_cache_dir: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "COOLDOWN", 7)

    assert not run_pipx_cli([
        "install",
        "--backend",
        "pip",
        "--cooldown",
        "0",
        f"--pip-args=--no-index --find-links={package_cache_dir}",
        PKG["pycowsay"]["spec"],
    ])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert ("--uploaded-prior-to" in caplog.text, metadata.cooldown_days) == (False, 0)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_env_cooldown_outranks_recorded(
    package_cache_dir: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"
    assert not run_pipx_cli(["install", "--backend", "pip", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    caplog.clear()

    monkeypatch.setattr(main, "COOLDOWN", 3)
    assert not run_pipx_cli(["install", "--backend", "pip", "--force", pip_args, PKG["pycowsay"]["spec"]])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert ("--uploaded-prior-to P3D" in caplog.text, metadata.cooldown_days) == (True, 3)


@pytest.mark.parametrize("value", [pytest.param("-1", id="negative"), pytest.param("invalid", id="not-an-integer")])
def test_install_rejects_invalid_cooldown(value: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="2"):
        run_pipx_cli(["install", "--cooldown", value, "pycowsay"])

    assert "--cooldown must be a non-negative integer" in capsys.readouterr().err


@pytest.mark.parametrize("editable", [pytest.param(False, id="wheel"), pytest.param(True, id="editable")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_source_from_pylock(
    make_pylock: Callable[[str, str], Path], make_project_with_dependency: Callable[[str], Path], editable: bool
) -> None:
    project: Final[Path] = make_project_with_dependency("pycowsay==0.0.0.2")
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert not run_pipx_cli(["install", *(["--editable"] if editable else []), "--lock", str(lock_file), str(project)])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "empty-project").main_package
    assert (metadata.package_version, metadata.lock_file, metadata.apps, metadata.pip_args) == (
        "0.1.0",
        lock_file.resolve(),
        [app_name("empty-project")],
        ["--editable"] if editable else [],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_incomplete_pylock(
    make_pylock: Callable[[str, str], Path],
    make_project_with_dependency: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    project: Final[Path] = make_project_with_dependency("black==22.8.0")
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert run_pipx_cli(["install", "--lock", str(lock_file), str(project)])

    assert (
        "does not satisfy empty-project" in capsys.readouterr().err,
        (paths.CTX.venvs / "empty-project").exists(),
    ) == (True, False)


@pytest.mark.parametrize(
    ("package_spec", "environment", "expected_error"),
    [
        pytest.param("pycowsay==999", "pycowsay", r"does\s+not\s+satisfy\s+pycowsay==999", id="version"),
        pytest.param("black", "black", r"does\s+not\s+contain\s+black", id="package"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_target_outside_pylock(
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    package_spec: str,
    environment: str,
    expected_error: str,
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert run_pipx_cli(["install", "--lock", str(lock_file), package_spec])

    error: Final[str] = unwrap_log_text(capsys.readouterr().err)
    assert (
        re.search(expected_error, error) is not None,
        (paths.CTX.venvs / environment).exists(),
    ) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_invalid_pylock(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (lock_file := tmp_path / "pylock.toml").write_text("invalid = true\n", encoding="utf-8")

    assert run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])

    assert (
        "Error installing packages from" in unwrap_log_text(capsys.readouterr().err),
        (paths.CTX.venvs / "pycowsay").exists(),
    ) == (True, False)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["install", "--force", "pycowsay"], id="force"),
        pytest.param(["reinstall", "pycowsay"], id="reinstall"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_reapplies_recorded_pylock(make_pylock: Callable[[str, str], Path], command: list[str]) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    (marker := paths.CTX.venvs / "pycowsay" / "marker").touch()

    assert not run_pipx_cli(command)

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (marker.exists(), metadata.package_version, metadata.lock_file) == (
        False,
        "0.0.0.2",
        lock_file.resolve(),
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_restores_environment_after_pylock_mismatch(make_pylock: Callable[[str, str], Path]) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    (marker := paths.CTX.venvs / "pycowsay" / "marker").touch()

    assert run_pipx_cli(["install", "--force", "--lock", str(lock_file), "pycowsay==999"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (marker.exists(), metadata.package_version, metadata.lock_file) == (
        True,
        "0.0.0.2",
        lock_file.resolve(),
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_skips_pylock(
    make_pylock: Callable[[str, str], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["install", "--upgrade", "pycowsay==999"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (
        "Not upgrading locked package pycowsay. Update its lock file and run `pipx reinstall pycowsay`."
        in unwrap_log_text(capsys.readouterr().out),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_cooldown_for_recorded_pylock(
    make_pylock: Callable[[str, str], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["install", "--force", "--cooldown", "7", "pycowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (
        "--cooldown cannot modify a locked environment" in unwrap_log_text(capsys.readouterr().err),
        metadata.package_version,
        metadata.lock_file,
    ) == (True, "0.0.0.2", lock_file.resolve())


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_env_cooldown_ignored_for_pylock(
    make_pylock: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "COOLDOWN", 7)
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "pycowsay").main_package
    assert (metadata.cooldown_days, metadata.lock_file) == (None, lock_file.resolve())


@pytest.mark.parametrize(
    ("package_args", "created_name", "lock_name", "expected_error"),
    [
        pytest.param(
            ["pycowsay", "black"],
            "pylock.test.toml",
            "pylock.test.toml",
            "--lock accepts one package spec",
            id="packages",
        ),
        pytest.param(
            ["--preinstall", "black", "pycowsay"],
            "pylock.test.toml",
            "pylock.test.toml",
            "--lock cannot be combined with --preinstall",
            id="preinstall",
        ),
        pytest.param(
            ["--upgrade", "pycowsay"],
            "pylock.test.toml",
            "pylock.test.toml",
            "--lock cannot be combined with --upgrade",
            id="upgrade",
        ),
        pytest.param(
            ["--cooldown", "7", "pycowsay"],
            "pylock.test.toml",
            "pylock.test.toml",
            "--lock cannot be combined with --cooldown",
            id="cooldown",
        ),
        pytest.param(["pycowsay"], "lock.toml", "lock.toml", "Lock files must be named", id="name"),
        pytest.param(["pycowsay"], "pylock.test.toml", "pylock.missing.toml", "Lock file does not exist", id="missing"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_invalid_pylock_options(
    make_pylock: Callable[[str, str], Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    package_args: list[str],
    created_name: str,
    lock_name: str,
    expected_error: str,
) -> None:
    make_pylock("pycowsay", "0.0.0.2").rename(tmp_path / created_name)

    assert run_pipx_cli(["install", "--lock", str(tmp_path / lock_name), *package_args])

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
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_missing_expected_app_rolls_back(
    capsys: pytest.CaptureFixture[str], app_args: list[str], expected_error: str
) -> None:
    return_code: Final[int] = run_pipx_cli(["install", *app_args, PKG["pycowsay"]["spec"]])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        return_code,
        f"Package pycowsay does not provide {expected_error}. Available apps: pycowsay." in error,
        (paths.CTX.venvs / "pycowsay").exists(),
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
    ) == (1, True, False, False)


@pytest.mark.parametrize(
    ("package_spec", "setup_commands"),
    [
        pytest.param("pycowsay>=0", [], id="satisfied"),
        pytest.param("pycowsay==999", [["pin", "pycowsay"]], id="pinned"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_records_expected_app_without_package_change(
    package_spec: str, setup_commands: list[list[str]]
) -> None:
    for command in [["install", PKG["pycowsay"]["spec"]], *setup_commands]:
        assert not run_pipx_cli(command)

    assert not run_pipx_cli(["install", "--upgrade", "--app", "pycowsay", package_spec])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.expected_apps == ["pycowsay"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_accepts_expected_dependency_app(local_extras_wheel: Path) -> None:
    assert not run_pipx_cli(["install", "--include-deps", "--app", "pycowsay", f"{local_extras_wheel}[cow]"])

    assert PipxMetadata(paths.CTX.venvs / "repeatme").main_package.expected_apps == ["pycowsay"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_reexposes_expected_dependency_resources(
    root: Path, tmp_path: Path, local_manpage_wheel: Path
) -> None:
    project: Final[Path] = tmp_path / "expected-dependency-app"
    shutil.copytree(root / "testdata/empty_project", project)
    pyproject: Final[Path] = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'requires-python = ">=3.10"\n',
            f'dependencies = [\n  "local-manpage @ {local_manpage_wheel.as_uri()}",\n]\nrequires-python = ">=3.10"\n',
        ),
        encoding="utf-8",
    )
    assert not run_pipx_cli(["install", "--include-deps", "--app", "local-manpage", str(project)])
    app_path: Final[Path] = paths.CTX.bin_dir / app_name("local-manpage")
    man_path: Final[Path] = paths.CTX.man_dir / "man1/local-manpage.1"
    app_path.unlink()
    man_path.unlink()
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "0.1.0"', 'version = "0.2.0"'),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["install", "--upgrade", str(project)])

    assert (app_path.exists(), man_path.exists()) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_removes_dropped_app(two_app_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", str(two_app_project)])
    drop_extra_app(two_app_project)
    assert not run_pipx_cli(["install", "--upgrade", str(two_app_project)])
    capsys.readouterr()

    assert not run_pipx_cli(["list"])

    assert (
        sorted(path.name for path in paths.CTX.bin_dir.iterdir()),
        "empty-project-extra" in capsys.readouterr().out,
    ) == ([app_name("empty-project")], False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_expected_app_rejects_multiple_specs(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--app", "pycowsay", "pycowsay", PKG["black"]["spec"]])

    assert (
        "--app accepts one package spec" in capsys.readouterr().err,
        (paths.CTX.venvs / "pycowsay").exists(),
        (paths.CTX.venvs / "black").exists(),
    ) == (True, False, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_force_preserves_expected_app() -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])

    assert not run_pipx_cli(["install", "--force", PKG["pycowsay"]["spec"]])

    assert (
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.expected_apps,
        tuple(paths.CTX.venvs.glob(".pycowsay-*-pipx-backup")),
    ) == (["pycowsay"], ())


@pytest.mark.parametrize("locked", [pytest.param(False, id="plain"), pytest.param(True, id="lock")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_force_keeps_pin(make_pylock: MakePylock, locked: bool) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay"])
    lock_args: Final[list[str]] = ["--lock", str(make_pylock("pycowsay", "0.0.0.2"))] if locked else []

    assert not run_pipx_cli(["install", "--force", *lock_args, PKG["pycowsay"]["spec"]])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pinned


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_backup_failure_preserves_existing_environment(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", PKG["pycowsay"]["spec"]])
    mocker.patch("pipx.commands.transaction.copytree", autospec=True, side_effect=OSError("disk full"))

    assert run_pipx_cli(["install", "--force", PKG["pycowsay"]["spec"]])

    assert (
        "pipx could not back up environment pycowsay: disk full" in capsys.readouterr().err,
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.expected_apps,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
    ) == (True, ["pycowsay"], True)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["install", "--force", "{project}"], id="install-force"),
        pytest.param(["install", "--upgrade", "{project}"], id="install-upgrade"),
        pytest.param(["upgrade", "empty-project"], id="upgrade"),
        pytest.param(["reinstall", "empty-project"], id="reinstall"),
    ],
)
def test_install_missing_recorded_app_restores_existing_environment(
    missing_expected_app_project: Path,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
) -> None:
    assert run_pipx_cli([part.format(project=missing_expected_app_project) for part in command])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "empty-project").main_package
    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        "Package empty-project does not provide expected app empty-project. Available apps: none." in error,
        metadata.package_version,
        metadata.expected_apps,
        metadata.apps,
        (paths.CTX.bin_dir / app_name("empty-project")).exists(),
    ) == (True, "0.1.0", ["empty-project"], [app_name("empty-project")], True)


@pytest.fixture
def missing_expected_app_project(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while the project is built
    capsys: pytest.CaptureFixture[str],
    root: Path,
    tmp_path: Path,
) -> Path:
    project: Final[Path] = tmp_path / "expected-app-project"
    shutil.copytree(root / "testdata/empty_project", project)
    assert not run_pipx_cli(["install", "--app", "empty-project", str(project)])
    capsys.readouterr()

    pyproject: Final[Path] = project / "pyproject.toml"
    pyproject.write_text(
        pyproject
        .read_text(encoding="utf-8")
        .replace('version = "0.1.0"', 'version = "0.2.0"')
        .replace('scripts.empty-project = "empty_project.main:cli"\n', "")
        .replace('entry-points."pipx.run".empty-project = "empty_project.main:cli"\n', ""),
        encoding="utf-8",
    )
    return project


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_same_package_twice_no_force(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    out: Final[str] = capsys.readouterr().out
    assert ("already seems to be installed" in out, "pipx upgrade" in out, "0.0.0.2" in out) == (True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_installs_missing_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--upgrade", PKG["black"]["spec"]])
    assert "installed package black 22.8.0" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_reconciles_package_spec(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])

    assert not run_pipx_cli(["install", "--upgrade", "--upgrade-strategy=eager", "black==22.10.0"])
    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "black").main_package
    assert (
        "upgraded package black from 22.8.0 to 22.10.0" in capsys.readouterr().out,
        metadata.package_version,
        metadata.pip_args,
    ) == (True, "22.10.0", [])

    assert not run_pipx_cli(["install", "--upgrade", "black<22.9"])
    assert (
        "upgraded package black from 22.10.0 to 22.8.0" in capsys.readouterr().out,
        PipxMetadata(paths.CTX.venvs / "black").main_package.package_version,
    ) == (True, "22.8.0")


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_multiple_existing(capsys: pytest.CaptureFixture[str]) -> None:
    package_specs: Final[list[str]] = [PKG["black"]["spec"], PKG["pycowsay"]["spec"]]
    assert run_pipx_cli(["install", *package_specs]) == EXIT_CODE_OK
    capsys.readouterr()

    assert run_pipx_cli(["install", "--upgrade", *package_specs]) == EXIT_CODE_OK
    output: Final[str] = capsys.readouterr().out
    assert ("black 22.8.0 already satisfies" in output, "pycowsay 0.0.0.2 already satisfies" in output) == (
        True,
        True,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_reuses_empty_environment_dir() -> None:
    (paths.CTX.venvs / "pycowsay").mkdir(parents=True)
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"]]),
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.package,
    ) == (EXIT_CODE_OK, "pycowsay")


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_satisfied_spec_is_offline(capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    check_shared: Final = mocker.patch.object(Venv, "check_upgrade_shared_libs", autospec=True)
    upgrade_package: Final = mocker.patch.object(Venv, "upgrade_package", autospec=True)

    assert not run_pipx_cli(["install", "--upgrade", "black>=22,<23"])

    assert (
        "black 22.8.0 already satisfies black>=22,<23" in capsys.readouterr().out,
        check_shared.call_count,
        upgrade_package.call_count,
    ) == (True, 0, 0)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_strategy_requires_upgrade(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        run_pipx_cli(["install", "--upgrade-strategy=eager", PKG["black"]["spec"]]),
        "--upgrade-strategy requires --upgrade" in capsys.readouterr().err,
    ) == (1, True)


@pytest.mark.parametrize(
    "index_args",
    [
        pytest.param(["--index-url", ""], id="index-url"),
        pytest.param(["--pip-args=--index-url="], id="index-in-pip-args"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_rejects_empty_index(capsys: pytest.CaptureFixture[str], index_args: list[str]) -> None:
    assert run_pipx_cli(["install", *index_args, "pycowsay"])

    assert ("--index-url is empty" in capsys.readouterr().err, (paths.CTX.venvs / "pycowsay").exists()) == (
        True,
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_existing_package_skips_shared_lib_maintenance(mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", PKG["pycowsay"]["spec"]]) == 0
    mocker.patch.object(shared_libs.SHARED_LIBS, "has_been_updated_this_run", False)
    mocker.patch(
        "pipx.shared_libs.time.time",
        return_value=shared_libs.SHARED_LIBS.pip_path.stat().st_mtime + shared_libs.SHARED_LIBS_MAX_AGE_SEC + 1,
    )
    run_subprocess: Final = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ModuleSpec", stderr=""),
    )

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])

    run_subprocess.assert_not_called()


@pytest.mark.usefixtures("pipx_temp_env")
def test_include_deps() -> None:
    assert not run_pipx_cli(["install", "requests==2.31.0", "--include-deps"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_include_resources_from_dependency(
    local_extras_wheel: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"

    assert not run_pipx_cli(["install", package, "--include-resources-from", "PyCowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.bin_dir / app_name("black")).exists(),
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
    ) == (["pycowsay"], True, False, True)
    capsys.readouterr()
    assert not run_pipx_cli(["list"])
    output: Final[str] = capsys.readouterr().out
    assert (f"    - {app_name('pycowsay')}" in output, f"    - {app_name('black')}" in output) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_force_replaces_included_dependency_resources(local_extras_wheel: Path) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["install", "--force", package, "--include-resources-from", "black"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
        (paths.CTX.bin_dir / app_name("black")).exists(),
    ) == (["black"], False, False, True)


def test_install_preserves_colliding_dependency_resource(
    copied_dependency_resource: tuple[Path, bytes],
    local_extras_wheel: Path,
) -> None:
    exposed_app, first_contents = copied_dependency_resource
    assert not run_pipx_cli(["install", f"{local_extras_wheel}[cow]", "--include-deps"])

    assert exposed_app.read_bytes() == first_contents


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_include_resources_from_missing_dependency_rolls_back(
    local_extras_wheel: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    package: Final[str] = f"{local_extras_wheel}[cow]"

    assert run_pipx_cli(["install", package, "--include-resources-from", "black"])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        "Cannot expose resources from black for package repeatme. "
        "Dependencies with apps, manual pages, or shell completions: pycowsay." in error,
        (paths.CTX.venvs / "repeatme").exists(),
    ) == (True, False)


@pytest.mark.parametrize(
    ("package_name", "package_spec"),
    [
        pytest.param(
            "zest-releaser",
            PKG["zest-releaser"]["spec"],
            marks=[
                pytest.mark.skipif(
                    sys.platform == "darwin",
                    reason="Skipping zest-releaser due to missing Python 3.13 wheel for cmarkgfm on macOS",
                ),
                pytest.mark.skipif(
                    sys.version_info >= (3, 15),
                    reason="Skipping zest-releaser due to missing Python 3.15 wheel for comrak",
                ),
            ],
        ),
        pytest.param("tox-ini-fmt", PKG["tox-ini-fmt"]["spec"]),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_name_tricky_characters(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    package_name: str,
    package_spec: str,
) -> None:
    install_packages(capsys, caplog, [package_spec], [package_name])


@pytest.mark.usefixtures("pipx_temp_env")
def test_extra(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "nox[tox_to_nox]==2023.4.22", "--include-deps"])
    assert f"- {app_name('tox')}\n" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_local_extra(capsys: pytest.CaptureFixture[str], local_extras_project: Path) -> None:
    assert not run_pipx_cli(["install", f"{local_extras_project}[cow]", "--include-deps"])
    out: Final[str] = capsys.readouterr().out
    assert (f"- {app_name('pycowsay')}\n" in out, f"- {Path('man6/pycowsay.6')}\n" in out) == (True, True)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param(
            "uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_bare_local_wheel_extra(
    local_extras_wheel: Path, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    monkeypatch.chdir(local_extras_wheel.parent)

    assert not run_pipx_cli(["install", "--backend", backend, f"{local_extras_wheel.name}[cow]", "--include-deps"])

    assert Venv(paths.CTX.venvs / "repeatme").has_package("pycowsay")


@pytest.mark.usefixtures("pipx_temp_env")
def test_path_warning(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "is not on your PATH environment variable" not in unwrap_log_text(caplog.text)

    monkeypatch.setenv("PATH", "")
    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    assert "is not on your PATH environment variable" in unwrap_log_text(caplog.text)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_existing_symlink_points_to_existing_wrong_location_warning(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    paths.CTX.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.CTX.bin_dir / "pycowsay").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        "File exists at" in unwrap_log_text(caplog.text),
        "symlink missing or pointing to unexpected location" in captured.out,
        # the bin dir is on PATH, so a symlink to the wrong location must not trigger the PATH warning
        "is not on your PATH environment variable" in captured.err,
    ) == (True, True, False)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_existing_man_page_symlink_points_to_existing_wrong_location_warning(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    (paths.CTX.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.CTX.man_dir / "man6" / "pycowsay.6").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    assert (
        "File exists at" in unwrap_log_text(caplog.text),
        "symlink missing or pointing to unexpected location" in capsys.readouterr().out,
    ) == (True, True)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_existing_symlink_points_to_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    paths.CTX.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.CTX.bin_dir / "pycowsay").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    # pipx replaces a dangling symlink without a warning
    assert "symlink missing or pointing to unexpected location" not in capsys.readouterr().out


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_existing_man_page_symlink_points_to_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    (paths.CTX.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.CTX.man_dir / "man6" / "pycowsay.6").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    # pipx replaces a dangling symlink without a warning
    assert "symlink missing or pointing to unexpected location" not in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_pip_args_forwarded_to_shared_libs(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    # an empty pipx home makes the next command upgrade the shared libraries
    assert shared_libs.SHARED_LIBS.needs_upgrade

    return_code: Final[int] = run_pipx_cli(["install", "--verbose", "--pip-args=--no-index", "pycowsay"])

    assert (
        return_code != 0,
        "Upgrading shared libraries in" in caplog.text,
        "ERROR: Could not find a version that satisfies the requirement pip" in capsys.readouterr().err,
        "Failed to upgrade shared libraries" in caplog.text,
    ) == (True, True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_pip_args_forwarded_to_package_name_determination(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli([
        "install",
        "https://github.com/psf/black/archive/22.8.0.zip",
        "--verbose",
        "--pip-args='--asdf'",
    ])
    err: Final[str] = capsys.readouterr().err
    assert ("--asdf" in err, "Cannot determine package name from spec" in err) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_url_refuses_wheel_whose_data_files_rename_it(
    make_wheel: Callable[[dict[str, str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    metadata: Final[str] = "Metadata-Version: 2.1\nName: {}\nVersion: 1\n"
    wheel: Final[Path] = make_wheel({
        "foo_bar_x.py": "",
        "foo_bar_x-1.dist-info/METADATA": metadata.format("foo-bar-x"),
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/RECORD": "",
        "foo_bar_x-1.data/purelib/foo_bar_x-1.dist-info/METADATA": metadata.format("pycowsay"),
    })

    assert run_pipx_cli(["install", "--backend", "pip", wheel.as_uri()])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert ("declares the name 'pycowsay'" in error, list(paths.CTX.venvs.glob("*"))) == (True, [])


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows only")
@pytest.mark.usefixtures("pipx_temp_env")
def test_pip_args_with_windows_path(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli([
        "install",
        "pycowsay",
        "--verbose",
        "--pip-args='--no-index --find-links=D:\\TEST\\DIR'",
    ])
    assert r"D:\\TEST\\DIR" in capsys.readouterr().err


@pytest.mark.parametrize("constraint_flag", ["-c ", "--constraint ", "--constraint="])
@pytest.mark.usefixtures("pipx_temp_env")
def test_pip_args_with_constraint_relative_path(
    constraint_flag: str, tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    (constraints_file := tmp_path / "constraints.txt").write_text("black!=22.10.0", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["install", f"--pip-args='{constraint_flag}constraints.txt'", "black"])

    assert (
        f"{constraint_flag}{constraints_file}" in caplog.text,
        PipxMetadata(paths.CTX.venvs / "black").main_package.package_version,
    ) == (True, "22.8.0")


@pytest.mark.usefixtures("pipx_temp_env")
def test_pip_args_with_attached_constraint_records_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (constraint_file := tmp_path / "constraints.txt").write_text("pycowsay==0.0.0.2", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert (
        run_pipx_cli(["install", "--pip-args=-cconstraints.txt", PKG["pycowsay"]["spec"]]),
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args[:1],
    ) == (0, [f"-c{constraint_file}"])


@pytest.mark.parametrize("constraint_flag", ["-c ", "--constraint ", "--constraint="])
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_pip_args_with_wrong_constraint_fail(
    constraint_flag: str, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    constraint_file_name: Final[str] = "constraints.txt"
    monkeypatch.chdir(tmp_path)

    assert run_pipx_cli(["install", f"--pip-args='{constraint_flag}{constraint_file_name}'", "pycowsay"])

    # pip phrases this as "requirements file" (<26) or "constraint file" (>=26), so match the common part
    assert f"[Errno 2] No such file or directory: {str(tmp_path / constraint_file_name)!r}" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    outputs: Final[list[str]] = []
    for suffix in ("_a", "_b"):
        assert not run_pipx_cli(["install", PKG["pbr"]["spec"], f"--suffix={suffix}"])
        outputs.append(capsys.readouterr().out)

    name_a, name_b = app_name("pbr_a"), app_name("pbr_b")
    assert (
        f"- {name_a}" in outputs[0],
        f"- {name_b}" in outputs[1],
        (paths.CTX.bin_dir / name_a).exists(),
        (paths.CTX.bin_dir / name_b).exists(),
    ) == (True, True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_man_page_install(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert (
        f"- {Path('man6/pycowsay.6')}" in capsys.readouterr().out,
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
    ) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_editable_install_links_man_pages(capsys: pytest.CaptureFixture[str], local_manpage_project: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", local_manpage_project.as_posix()])
    out: Final[str] = capsys.readouterr().out
    exposed_man_page: Final[Path] = paths.CTX.man_dir / "man1" / "local-manpage.1"
    assert (
        f"- {app_name('local-manpage')}\n" in out,
        f"- {Path('man1/local-manpage.1')}" in out,
        (paths.CTX.venvs / "local-manpage" / "share" / "man" / "man1" / "local-manpage.1").exists(),
        exposed_man_page.exists(),
    ) == (True, True, True, True)

    assert not run_pipx_cli(["uninstall", "local-manpage"])
    assert not exposed_man_page.exists()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_uv_failure_shows_uv_error(
    make_project_with_dependency: Callable[[str], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    project: Final[Path] = make_project_with_dependency("no-such-dependency-for-pipx")

    assert run_pipx_cli(["install", "--backend", "uv", str(project)])

    assert re.search(
        r"Some possibly relevant errors from uv install:\n\s+error: .*\n.*no-such-dependency-for-pipx",
        capsys.readouterr().err,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_in_terminal_keeps_installer_output_off_screen(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # patch each module's copy of the flag so the test holds wherever the terminal check is read
    for module in [
        module for name, module in sys.modules.items() if name.startswith("pipx") and hasattr(module, "STDERR_IS_TTY")
    ]:
        monkeypatch.setattr(module, "STDERR_IS_TTY", True)

    assert not run_pipx_cli(["install", "--backend", "pip", PKG["pycowsay"]["spec"]])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert ("installing pycowsay" in captured.err, "Collecting pycowsay" in captured.out + captured.err) == (
        True,
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize("flags", [pytest.param([], id="plain"), pytest.param(["--verbose"], id="verbose")])
def test_install_pip_failure_prints_pip_error_once(
    make_project_with_dependency: Callable[[str], Path], capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    project: Final[Path] = make_project_with_dependency("no-such-dependency-for-pipx")

    assert run_pipx_cli(["install", "--backend", "pip", *flags, str(project)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out + captured.err).count("No matching distribution found for no-such-dependency-for-pipx") == 1


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize("flags", [pytest.param([], id="plain"), pytest.param(["--verbose"], id="verbose")])
def test_install_uv_failure_prints_uv_error_once(
    make_project_with_dependency: Callable[[str], Path], capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    project: Final[Path] = make_project_with_dependency("no-such-dependency-for-pipx")

    assert run_pipx_cli(["install", "--backend", "uv", *flags, str(project)])

    assert capsys.readouterr().err.count("No solution found when resolving dependencies") == 1


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_verbose_masks_index_credentials(
    make_project_with_dependency: Callable[[str], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    project: Final[Path] = make_project_with_dependency("no-such-dependency-for-pipx")
    index_args: Final[str] = "--no-index --index-url=https://alice:s3cr3t@127.0.0.1:9/simple/"

    assert run_pipx_cli(["install", "--verbose", "--backend", "uv", f"--pip-args={index_args}", str(project)])

    output: Final[str] = capsys.readouterr().err + current_log_file().read_text(encoding="utf-8")
    assert ("****:****@127.0.0.1" in output, "s3cr3t" in output) == (True, False)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize(
    "spec",
    [
        pytest.param("https://alice:s3cr3t@127.0.0.1:9/pkg-1.0-py3-none-any.whl", id="url"),
        pytest.param("pkg @ https://alice:s3cr3t@127.0.0.1:9/pkg-1.0-py3-none-any.whl", id="named-url"),
    ],
)
@pytest.mark.parametrize("flags", [pytest.param([], id="quiet"), pytest.param(["--verbose"], id="verbose")])
def test_install_masks_spec_credentials(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, spec: str, flags: list[str]
) -> None:
    monkeypatch.setenv("UV_HTTP_RETRIES", "0")

    assert run_pipx_cli(["install", "--backend", "uv", *flags, spec])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    log: Final[str] = current_log_file().read_text(encoding="utf-8")
    assert "s3cr3t" not in captured.out + captured.err + log


@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize(
    ("backend", "flags"),
    [
        pytest.param("pip", [], id="pip"),
        pytest.param("pip", ["--verbose"], id="pip-verbose"),
        # uv --verbose repeats the build error in its own debug log, so only its plain run isolates pipx's reporting
        pytest.param(
            "uv", [], id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
        ),
    ],
)
def test_install_name_probe_failure_prints_the_error_once(
    project_failing_to_build: Path, capsys: pytest.CaptureFixture[str], backend: str, flags: list[str]
) -> None:
    assert run_pipx_cli(["install", *flags, "--backend", backend, str(project_failing_to_build)])

    assert capsys.readouterr().err.count("pipx-test-build-failure") == 1


@pytest.fixture
def project_failing_to_build(tmp_path: Path) -> Path:
    # setup.py only, so pipx learns the name by installing it, and the build fails before anything installs
    (project := tmp_path / "fails-to-build").mkdir()
    (project / "setup.py").write_text("raise SystemExit('pipx-test-build-failure')\n", encoding="utf-8")
    return project


@pytest.mark.usefixtures("pipx_temp_env")
@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param(
            "uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
        ),
    ],
)
@pytest.mark.parametrize("flags", [pytest.param([], id="plain"), pytest.param(["--verbose"], id="verbose")])
def test_install_json_failure_carries_the_installer_error(
    make_project_with_dependency: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
    backend: str,
    flags: list[str],
) -> None:
    project: Final[Path] = make_project_with_dependency("no-such-dependency-for-pipx")

    assert run_pipx_cli(["install", "--output", "json", *flags, "--backend", backend, str(project)])

    assert "no-such-dependency-for-pipx" in json.loads(capsys.readouterr().out)["errors"][0]["message"]


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_failure_keeps_what_the_terminal_showed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project := tmp_path / "redraws").mkdir()
    (project / "setup.py").write_text(
        "import sys\nsys.stderr.write('pipx-redrawn-frame\\rpipx-final-frame\\n')\nraise SystemExit(1)\n",
        encoding="utf-8",
    )

    assert run_pipx_cli(["install", "--output", "json", "--verbose", "--backend", "uv", str(project)])

    message: Final[str] = json.loads(capsys.readouterr().out)["errors"][0]["message"]
    assert ("pipx-final-frame" in message, "pipx-redrawn-frame" in message) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_pip_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "weblate==4.3.1", "--verbose"])

    err: Final[str] = capsys.readouterr().err
    pip_log_file_match: Final = re.search(r"Full pip output in file:\s+(\S.+)$", err, re.MULTILINE)
    assert pip_log_file_match
    assert (
        "Fatal error from pip" in err,
        Path(pip_log_file_match[1]).exists(),
        re.search(r"pip (failed|seemed to fail) to build package", err) is not None,
    ) == (True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_local_archive(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], local_extras_wheel: Path
) -> None:
    monkeypatch.chdir(local_extras_wheel.parent)

    assert not run_pipx_cli(["install", "repeatme-0.1-py3-none-any.whl"])
    assert f"- {app_name('repeatme')}\n" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_local_project_uses_built_name_when_backend_ignores_project_table(
    project_ignoring_project_table: Path,
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", str(project_ignoring_project_table)])

    assert (
        PipxMetadata(paths.CTX.venvs / "real-pkg").main_package.package,
        (paths.CTX.bin_dir / app_name("realapp")).exists(),
    ) == ("real-pkg", True)


@pytest.mark.parametrize(
    ("backend", "package"),
    [
        pytest.param("pip", "Foo_Bar.X", id="pip"),
        pytest.param(
            "uv",
            "foo-bar-x",
            id="uv",
            marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH"),
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_local_wheel_records_installer_name(
    make_wheel: Callable[[dict[str, str]], Path], backend: str, package: str
) -> None:
    wheel: Final[Path] = make_wheel({
        "foo_bar_x/__init__.py": "def main() -> None:\n    pass\n",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: Foo_Bar.X\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/entry_points.txt": "[console_scripts]\nfoo-bar-x = foo_bar_x:main\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })

    assert not run_pipx_cli(["install", "--backend", backend, str(wheel)])

    assert (
        PipxMetadata(paths.CTX.venvs / "foo-bar-x").main_package.package,
        (paths.CTX.bin_dir / app_name("foo-bar-x")).exists(),
    ) == (package, True)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param("uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")),
    ],
)
@pytest.mark.parametrize(
    "directory",
    [
        pytest.param("scripts", id="plain"),
        pytest.param("scripts#123", id="hash"),
        pytest.param("Project #123", id="space-and-hash"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script(inline_script: Path, backend: str, directory: str) -> None:
    (script_dir := inline_script.parent / directory).mkdir()
    script: Final[Path] = inline_script.rename(script_dir / inline_script.name)
    assert not run_pipx_cli(["install", "--backend", backend, str(script)])

    app: Final[Path] = paths.CTX.bin_dir / app_name("hello")
    process: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [app],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (process.stdout, run_pipx_cli(["uninstall", "hello"]), app.exists()) == ("installed\n", 0, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_by_bare_relative_name(inline_script: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(inline_script.parent)

    assert (
        run_pipx_cli(["install", inline_script.name]),
        PipxMetadata(paths.CTX.venvs / "hello").main_package.package_or_url,
    ) == (0, str(inline_script.resolve()))


@pytest.mark.parametrize(
    "directory",
    [pytest.param("[1]", id="whole-name"), pytest.param("a[x]b", id="inside-name")],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_from_bracketed_directory(inline_script: Path, directory: str) -> None:
    (script_dir := inline_script.parent / directory).mkdir()
    script: Final[Path] = inline_script.rename(script_dir / inline_script.name)

    assert (
        run_pipx_cli(["install", str(script)]),
        run_pipx_cli(["reinstall", "hello"]),
        PipxMetadata(paths.CTX.venvs / "hello").main_package.package_or_url,
    ) == (0, 0, str(script.resolve()))


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_from_unexpanded_home(inline_script: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(inline_script.parent))
    monkeypatch.setenv("USERPROFILE", str(inline_script.parent))

    assert not run_pipx_cli(["install", f"~/{inline_script.name}"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_app_override(inline_script: Path) -> None:
    assert not run_pipx_cli(["install", "--app", "greet", str(inline_script)])

    assert (paths.CTX.bin_dir / app_name("greet")).is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_url(inline_script: Path, mocker: MockerFixture) -> None:
    response: Final[MagicMock] = mocker.MagicMock(
        length=0,
        **{
            "read.return_value": inline_script.read_bytes(),
            "headers.get_content_charset.return_value": "utf-8",
        },
    )
    response.__enter__.return_value = response
    mocker.patch("urllib.request.urlopen", autospec=True, return_value=response)

    assert not run_pipx_cli(["install", "https://example.invalid/hello.py"])

    assert (paths.CTX.bin_dir / app_name("hello")).is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_url_error(mocker: MockerFixture, capsys: pytest.CaptureFixture[str]) -> None:
    mocker.patch("urllib.request.urlopen", autospec=True, side_effect=OSError("unavailable"))

    assert run_pipx_cli(["install", "--output", "json", "https://example.invalid/hello.py"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    failure: Final[str] = json.loads(captured.out)["errors"][0]["message"]
    assert ("Unable to read script" in " ".join(failure.split()), (paths.CTX.venvs / "hello").exists()) == (
        True,
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_rolls_back_without_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script: Final[Path] = tmp_path / "plain.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    assert run_pipx_cli(["install", "--output", "json", str(script)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    failure: Final[str] = json.loads(captured.out)["errors"][0]["message"]
    assert ("has no PEP 723" in " ".join(failure.split()), (paths.CTX.venvs / "plain").exists()) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_rolls_back_obsolete_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script: Final[Path] = tmp_path / "obsolete.py"
    script.write_text("# /// pyproject\n# dependencies = []\n# ///\n", encoding="utf-8")

    assert run_pipx_cli(["install", "--output", "json", str(script)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    failure: Final[str] = json.loads(captured.out)["errors"][0]["message"]
    assert ("obsolete" in failure, (paths.CTX.venvs / "obsolete").exists()) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_inline_script_from_pylock(inline_script: Path, make_pylock: Callable[[str, str], Path]) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")

    assert not run_pipx_cli(["install", "--lock", str(lock_file), str(inline_script)])

    metadata: Final[PackageInfo] = PipxMetadata(paths.CTX.venvs / "hello").main_package
    assert (metadata.lock_file, (paths.CTX.bin_dir / app_name("hello")).is_file()) == (lock_file.resolve(), True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install_changes(capsys: pytest.CaptureFixture[str], empty_project: Path, tmp_path: Path) -> None:
    with _served_archive_spec(empty_project) as package_spec:
        assert not run_pipx_cli(["install", package_spec])
    assert "0.1.0" in capsys.readouterr().out
    bumped_project: Final[Path] = tmp_path / "bumped_project"
    shutil.copytree(empty_project, bumped_project)
    pyproject: Final[Path] = bumped_project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "0.1.0"', 'version = "0.2.0"'), encoding="utf-8"
    )

    assert not run_pipx_cli(["install", str(bumped_project), "--force"])

    assert "0.1.0" not in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install_changes_editable(empty_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--editable", empty_project.as_posix()])
    assert "empty-project" in capsys.readouterr().out

    assert not run_pipx_cli(["install", "--editable", empty_project.as_posix(), "--force"])

    assert "Installing to existing venv 'empty-project'" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_multiple_packages_preserves_editable_for_local_package(empty_project: Path) -> None:
    assert (
        run_pipx_cli(["install", PKG["pycowsay"]["spec"], empty_project.as_posix(), "--editable"]),
        PipxMetadata(paths.CTX.venvs / "empty-project").main_package.pip_args,
    ) == (0, ["--editable"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_preinstall(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "--preinstall", "black", "nox"])
    assert "black" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_preinstall_cooldown(package_cache_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli([
        "install",
        "--preinstall",
        PKG["black"]["spec"],
        "--cooldown",
        "7",
        f"--pip-args=--no-index --find-links={package_cache_dir}",
        PKG["nox"]["spec"],
    ])

    assert (
        caplog.text.count("--uploaded-prior-to P7D"),
        PipxMetadata(paths.CTX.venvs / "nox").main_package.cooldown_days,
    ) == (2, 7)


@pytest.mark.usefixtures("pipx_temp_env")
def test_preinstall_multiple(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "--preinstall", "chardet", "--preinstall", "colorama", PKG["pycowsay"]["spec"]])
    assert ("chardet" in caplog.text, "colorama" in caplog.text) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_preinstall_specific_version(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "--preinstall", "black==22.8.0", "nox"])
    assert "black==22.8.0" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "pipx_session_shared_dir")
def test_do_not_wait_for_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIP_INDEX_URL", "http://127.0.0.1:8080/simple")
    # pip otherwise retries the refused connection five times with backoff
    monkeypatch.setenv("PIP_RETRIES", "0")
    assert run_pipx_cli(["install", "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_passed_python_and_force_flag_warning(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])

    assert not run_pipx_cli(["install", "--python", sys.executable, "--force", PKG["pycowsay"]["spec"]])

    assert "--python is ignored when --force is passed." in capsys.readouterr().out


@pytest.mark.parametrize(
    "setup_commands",
    [
        pytest.param([["install", PKG["pycowsay"]["spec"]]], id="existing"),
        pytest.param([], id="new"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_force_flag_without_python_does_not_warn(
    capsys: pytest.CaptureFixture[str], setup_commands: list[list[str]]
) -> None:
    for command in setup_commands:
        assert not run_pipx_cli(command)

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--force"])

    assert "--python is ignored when --force is passed." not in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install_python_warning_suggests_reinstall_of_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["install", "--force", "--python", sys.executable, PKG["pycowsay"]["spec"]])

    assert f"run `pipx reinstall pycowsay --python {sys.executable}` instead" in " ".join(
        capsys.readouterr().out.split()
    )


@SKIP_IF_WINDOWS
@pytest.mark.parametrize("locked", [pytest.param(False, id="plain"), pytest.param(True, id="locked")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_force_install_keeps_existing_interpreter(
    tmp_path: Path, make_pylock: Callable[[str, str], Path], locked: bool
) -> None:
    lock_args: Final[list[str]] = ["--lock", str(make_pylock("pycowsay", "0.0.0.2"))] if locked else []
    assert not run_pipx_cli(["install", *lock_args, PKG["pycowsay"]["spec"]])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    recorded: Final[Path | None] = PipxMetadata(venv_dir).source_interpreter
    (other_python := tmp_path / "python-other").symlink_to(sys.executable)

    assert not run_pipx_cli(["install", "--force", "--python", str(other_python), PKG["pycowsay"]["spec"]])

    assert PipxMetadata(venv_dir).source_interpreter == recorded


@pytest.mark.parametrize(
    ("python_version", "fetch_flag", "expect_deprecation"),
    [
        pytest.param("3.0", "--fetch-python=missing", False, id="3.0-fetch-python-missing"),
        pytest.param("3.1", "--fetch-python=missing", False, id="3.1-fetch-python-missing"),
        pytest.param("3.0", "--fetch-missing-python", True, id="3.0-deprecated-flag"),
    ],
)
@pytest.mark.usefixtures("mocked_github_api")
def test_install_fetch_missing_python_invalid(
    capsys: pytest.CaptureFixture[str], python_version: str, fetch_flag: str, expect_deprecation: bool
) -> None:
    assert run_pipx_cli(["install", "--python", python_version, fetch_flag, "pycowsay"])
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        f"No executable for the provided Python version '{python_version}' found" in captured.out,
        "--fetch-missing-python is deprecated" in captured.err,
    ) == (True, expect_deprecation)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_run_in_separate_directory(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("argparse.py").touch()

    install_packages(capsys, caplog, ["pycowsay"], ["pycowsay"])


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "python_version",
    [
        str(sys.version_info.major),
        f"{sys.version_info.major}.{sys.version_info.minor}",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_python_command_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], python_version: str
) -> None:
    monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    assert python_version in capsys.readouterr().out


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_python_command_version_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--python", "3.x", "--verbose", "pycowsay"])
    assert "Invalid Python version: 3.x" in capsys.readouterr().err


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_python_command_version_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    python_version: Final[str] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.dev"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    assert f"Unsupported Python version: {python_version}" in capsys.readouterr().err


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_python_command_version_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
    python_version: Final[str] = f"{sys.version_info.major + 99}.{sys.version_info.minor}"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    assert f"Command `python{python_version}` was not found" in capsys.readouterr().err


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_python_command_version_micro_mismatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
    python_version: Final[str] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro + 1}"
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    assert (
        f"It may not match the specified version {python_version} at the micro/patch level" in capsys.readouterr().err
    )


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_global_flag_before_subcommand_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_pipx_cli(["--global", "install", "pycowsay"])

    assert (exc_info.value.code, "unrecognized arguments: --global" in capsys.readouterr().err) == (2, True)


@pytest.mark.parametrize(
    "flag",
    [
        pytest.param("--global", marks=SKIP_IF_WINDOWS, id="global"),
        pytest.param("--skip-maintenance", id="skip-maintenance"),
        pytest.param("--verbose", id="verbose"),
        pytest.param("--quiet", id="quiet"),
    ],
)
@pytest.mark.parametrize(
    ("group", "subcommand"),
    [
        pytest.param("manifest", ["sync", "pipx.toml"], id="manifest"),
        pytest.param("interpreter", ["prune"], id="interpreter"),
        pytest.param("cache", ["purge"], id="cache"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_shared_flag_before_nested_subcommand_rejected(
    capsys: pytest.CaptureFixture[str], group: str, subcommand: list[str], flag: str
) -> None:
    # the subcommand's namespace used to overwrite the flag parsed by the group parser, silently dropping it
    with pytest.raises(SystemExit) as exc_info:
        run_pipx_cli([group, flag, *subcommand])

    assert (exc_info.value.code, f"unrecognized arguments: {flag}" in capsys.readouterr().err) == (2, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_quiet_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--quiet", "--quiet", "pycowsay"])
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        "installed package" in captured.out,
        "These apps are now" in captured.out,
        "done!" in captured.out,
        "done!" in captured.err,
    ) == (False, False, False, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["install"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "pycowsay",
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_reports_existing(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["install", "--output", "json", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["install"],
            "data": {
                "packages": [],
                "skipped": [
                    {
                        "environment": "pycowsay",
                        "package": "pycowsay",
                        "reason": "already-installed",
                    }
                ],
            },
            "pipx_result_version": "1",
            "errors": [],
            "exit_code": 0,
            "status": "success",
        },
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_reports_invalid_option(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--upgrade-strategy", "eager", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["install"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_install_failed",
                    "environment": "pycowsay",
                    "message": "--upgrade-strategy requires --upgrade",
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
def test_install_json_attributes_name_resolution_failure(
    empty_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing: Final[Path] = tmp_path / "missing.whl"

    assert run_pipx_cli(["install", "--output", "json", str(empty_project), str(missing)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out)["errors"][0]["environment"], captured.err) == (str(missing), "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_reports_missing_app(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--output", "json", "--app", "missing", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        json.loads(captured.out),
        captured.err,
        (paths.CTX.venvs / "pycowsay").exists(),
    ) == (
        {
            "command": ["install"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_install_failed",
                    "environment": "pycowsay",
                    "message": "Package pycowsay does not provide expected app missing. Available apps:\npycowsay.",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_reports_existing_upgrade_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "--suffix=-x", "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["install", "--output", "json", "--upgrade", "--app", "missing", "--suffix=-x", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out)["errors"], captured.err) == (
        [
            {
                "code": "package_install_failed",
                "environment": "pycowsay-x",
                "message": "Package pycowsay does not provide expected app missing. Available apps:\npycowsay.",
                "package": None,
            }
        ],
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_keyboard_interrupt_removes_environment(mocker: MockerFixture) -> None:
    mocker.patch.object(Venv, "install_package", autospec=True, side_effect=KeyboardInterrupt)

    assert (
        run_pipx_cli(["install", "pycowsay"]),
        (paths.CTX.venvs / "pycowsay").exists(),
    ) == (1, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_error_removes_environment(mocker: MockerFixture) -> None:
    mocker.patch.object(Venv, "install_package", autospec=True, side_effect=RuntimeError("failed"))

    with pytest.raises(RuntimeError, match="failed"):
        run_pipx_cli(["install", "pycowsay"])
    assert not (paths.CTX.venvs / "pycowsay").exists()


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_killed_before_recording_leaves_environment_unfinished(mocker: MockerFixture) -> None:
    # no handler rolls a kill back, which SystemExit stands in for
    mocker.patch.object(Venv, "install_package", autospec=True, side_effect=SystemExit(1))

    with pytest.raises(SystemExit):
        run_pipx_cli(["install", "pycowsay"])

    assert (paths.CTX.venvs / "pycowsay" / "pipx_unfinished").is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_leaves_recorded_environment_finished() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not (paths.CTX.venvs / "pycowsay" / "pipx_unfinished").exists()


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_install_skip_maintenance_without_index(
    capsys: pytest.CaptureFixture[str], package_cache_dir: Path, tmp_path: Path
) -> None:
    (wheelhouse := tmp_path / "wheelhouse").mkdir()
    wheel: Final = shutil.copy2(next(package_cache_dir.glob("pycowsay-*.whl")), wheelhouse)

    assert not run_pipx_cli([
        "install",
        "--skip-maintenance",
        str(wheel),
        f"--pip-args=--no-index --find-links={wheelhouse}",
    ])

    assert (
        "installed package pycowsay" in capsys.readouterr().out,
        shared_libs.shared_libs_auto_upgrade_disabled(),
    ) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_json_failure_reports_environment_without_url_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    spec: Final[str] = "http://u:s3cr3ttok@127.0.0.1:9/tool-1.0-py3-none-any.whl"

    assert run_pipx_cli(["install", "--output", "json", "--upgrade-strategy", "eager", spec])

    assert json.loads(capsys.readouterr().out)["errors"][0]["environment"] == redact_url_credentials(spec)
