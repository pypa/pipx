from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import textwrap
from typing import TYPE_CHECKING, Final

import pytest
from packaging.utils import canonicalize_name

from helpers import (
    PACKAGE_CACHE_DIR_NAME,
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    mock_legacy_venv,
    run_pipx_cli,
    skip_if_windows,
)
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from _pytest.capture import CaptureResult


@pytest.mark.usefixtures("installed_pycowsay")
def test_inject_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "--output", "json", "pycowsay", PKG["black"]["spec"]])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["inject"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.ctx.venvs / "pycowsay"),
                        "package": "black",
                        "status": "injected",
                        "version": "22.8.0",
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
def test_inject_json_reports_locked_environment(
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["inject", "--output", "json", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["inject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_inject_failed",
                    "environment": "pycowsay",
                    "message": (
                        f"Cannot inject into locked environment pycowsay. Update {lock_file} "
                        "and run `pipx reinstall pycowsay`."
                    ),
                    "package": "black",
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_inject_json_reports_already_installed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["inject", "--output", "json", "pycowsay", PKG["black"]["spec"]])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["inject"],
            "data": {
                "packages": [],
                "skipped": [
                    {
                        "environment": "pycowsay",
                        "package": "black",
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


@pytest.mark.usefixtures("installed_pycowsay")
def test_inject_json_reports_partial_failure(
    empty_project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_project: Final[Path] = tmp_path / "missing-project"
    assert run_pipx_cli(["inject", "--output", "json", "pycowsay", str(empty_project), str(missing_project)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        captured.err,
        json.loads(captured.out),
    ) == (
        "",
        {
            "command": ["inject"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.ctx.venvs / "pycowsay"),
                        "package": "empty-project",
                        "status": "injected",
                        "version": "0.1.0",
                    }
                ],
                "skipped": [],
            },
            "errors": [
                {
                    "code": "package_inject_failed",
                    "environment": "pycowsay",
                    "message": f"Unable to parse package spec: {missing_project}",
                    "package": str(missing_project),
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "partial",
        },
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_inject_json_reports_no_packages(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["inject", "--output", "json", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["inject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_inject_failed",
                    "environment": "pycowsay",
                    "message": "No packages have been specified.",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_inject_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "-qq", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        "injected package" not in captured.out,
        "done!" not in captured.err,
    ) == (True, True)


@pytest.fixture
def installed_pycowsay(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # required so the temp env is active while pycowsay is installed
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_rejects_pylock(
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["inject", "pycowsay", "black"])

    error = " ".join(capsys.readouterr().err.split())
    assert (
        "Cannot inject into locked environment pycowsay" in error and "`pipx reinstall pycowsay`" in error,
        PipxMetadata(paths.ctx.venvs / "pycowsay").injected_packages,
    ) == (True, {})


# Note that this also checks that packages used in other tests can be injected individually
@pytest.mark.parametrize(
    "pkg_spec",
    [
        PKG["black"]["spec"],
        PKG["nox"]["spec"],
        PKG["pylint"]["spec"],
        PKG["ipython"]["spec"],
        "jaraco.clipboard==2.0.1",  # tricky character
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_single_package(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    pkg_spec: str,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", pkg_spec])

    # Check arguments have been parsed correctly
    assert f"Injecting packages: {[pkg_spec]!r}" in caplog.text

    # Check it's actually being installed and into correct venv
    captured = capsys.readouterr()
    injected = re.findall(r"injected package (.+?) into venv pycowsay", captured.out)
    pkg_name = pkg_spec.split("=", 1)[0].replace(".", "-")  # assuming spec is always of the form <name>==<version>
    assert set(injected) == {pkg_name}


@pytest.mark.parametrize(
    ("backend", "suffix"),
    [
        pytest.param("pip", "", id="pip"),
        pytest.param(
            "uv",
            "_x",
            id="uv",
            marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH"),
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_main_package_extra(
    local_extras_project: Path,
    capsys: pytest.CaptureFixture[str],
    backend: str,
    suffix: str,
) -> None:
    assert not run_pipx_cli(["install", str(local_extras_project), "--backend", backend, f"--suffix={suffix}"])
    venv_dir = paths.ctx.venvs / canonicalize_name(f"repeatme{suffix}")
    environment = PipxMetadata(venv_dir).environment
    assert environment is not None
    assert not run_pipx_cli(["inject", environment, f"{local_extras_project}[cow]", "--backend", backend])
    assert not run_pipx_cli(["reinstall", environment])

    output = subprocess.run(
        [paths.ctx.bin_dir / app_name(f"repeatme{suffix}"), "hello"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--include-injected"])
    list_output = capsys.readouterr().out
    assert (
        "In cow, you said:" in output,
        "injected in venv" in list_output,
        environment,
    ) == (True, False, venv_dir.name)


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_inject_simple_global() -> None:
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["inject", "--global", "pycowsay", PKG["black"]["spec"]])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_simple_legacy_venv(
    capsys: pytest.CaptureFixture[str],
    metadata_version: str | None,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is not None:
        assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    else:
        # no metadata in venv should result in PipxError with message
        assert run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
        assert "Please uninstall and install" in capsys.readouterr().err


@pytest.mark.parametrize("with_suffix", [False, True])
@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_inject_include_apps(with_suffix: bool) -> None:
    install_args = []
    suffix = ""

    if with_suffix:
        suffix = "_x"
        install_args = [f"--suffix={suffix}"]

    assert not run_pipx_cli(["install", "pycowsay", *install_args])
    assert not run_pipx_cli(["inject", f"pycowsay{suffix}", PKG["black"]["spec"], "--include-deps"])

    if suffix:
        assert run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-deps"])

    assert not run_pipx_cli(["inject", f"pycowsay{suffix}", PKG["black"]["spec"], "--include-deps"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_include_resources_from_dependency(
    local_extras_project: Path,
    empty_project: Path,
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", str(empty_project)])

    assert not run_pipx_cli(["inject", "empty-project", package, "--include-resources-from", "PyCowsay"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "empty-project").injected_packages["repeatme"]
    assert (
        metadata.include_apps,
        metadata.include_resources_from,
        (paths.ctx.bin_dir / app_name("repeatme")).exists(),
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (True, ["pycowsay"], True, True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_main_package_preserves_included_dependency(
    local_extras_project: Path,
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["inject", "repeatme", f"{local_extras_project}[cow]"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert metadata.include_resources_from == ["pycowsay"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_force_replaces_included_dependency_resources(
    local_extras_project: Path,
    empty_project: Path,
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", str(empty_project)])
    assert not run_pipx_cli(["inject", "empty-project", package, "--include-resources-from", "pycowsay"])

    assert not run_pipx_cli(["inject", "empty-project", package, "--force", "--include-resources-from", "black"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "empty-project").injected_packages["repeatme"]
    assert (
        metadata.include_resources_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.man_dir / "man6" / "pycowsay.6").exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["black"], False, False, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_include_resources_from_missing_dependency_rolls_back(
    local_extras_project: Path,
    empty_project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", str(empty_project)])
    capsys.readouterr()
    package: Final[str] = f"{local_extras_project}[cow]"

    assert run_pipx_cli(["inject", "empty-project", package, "--include-resources-from", "black"])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    assert (
        "Cannot expose apps from black for package repeatme. Dependencies with apps or manual pages: pycowsay." in error
    )
    assert run_pipx_cli(["runpip", "empty-project", "show", "repeatme"])
    assert PipxMetadata(paths.ctx.venvs / "empty-project").injected_packages == {}


@pytest.mark.parametrize(
    "with_packages",
    [
        (),  # no extra packages
        ("black",),  # duplicate from requirements file
        ("ipython",),  # additional package
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_with_req_file(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    with_packages: tuple[str, ...],
) -> None:
    caplog.set_level(logging.INFO)

    req_file = tmp_path / "inject-requirements.txt"
    req_file.write_text(
        textwrap.dedent(
            f"""
                {PKG["black"]["spec"]} # a comment inline
                {PKG["nox"]["spec"]}

                {PKG["pylint"]["spec"]}
                # comment on separate line
            """
        ).strip()
    )
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli([
        "inject",
        "pycowsay",
        *(PKG[pkg]["spec"] for pkg in with_packages),
        "--requirement",
        str(req_file),
    ])

    packages = [
        ("black", PKG["black"]["spec"]),
        ("nox", PKG["nox"]["spec"]),
        ("pylint", PKG["pylint"]["spec"]),
    ]
    packages.extend((pkg, PKG[pkg]["spec"]) for pkg in with_packages)
    packages = sorted(set(packages))

    # Check arguments and files have been parsed correctly
    assert f"Injecting packages: {[p for _, p in packages]!r}" in caplog.text

    # Check they're actually being installed and into correct venv
    captured = capsys.readouterr()
    injected = re.findall(r"injected package (.+?) into venv pycowsay", captured.out)
    assert set(injected) == {pkg for pkg, _ in packages}


@pytest.mark.usefixtures("pipx_temp_env")
def test_force_inject_reinstalls_without_storing_force(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--pip-args=--no-cache-dir"])

    caplog.clear()
    assert not run_pipx_cli([
        "inject",
        "pycowsay",
        PKG["black"]["spec"],
        "--force",
        "--verbose",
        "--pip-args=--no-cache-dir",
    ])

    assert "--force-reinstall" in caplog.text

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert metadata.injected_packages["black"].pip_args == ["--no-cache-dir"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_inject_inherits_cooldown(
    root: Path,
    empty_project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    find_links: Final[Path] = root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    caplog.clear()

    assert not run_pipx_cli(["inject", "pycowsay", pip_args, str(empty_project)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        "--uploaded-prior-to P7D" in caplog.text,
        metadata.injected_packages["empty-project"].cooldown_days,
    ) == (True, 7)
