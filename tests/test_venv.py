from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Final
from venv import EnvBuilder

import pytest

from helpers import LEGACY_MAIN_PACKAGE, CurrentMetadata, run_pipx_cli
from package_info import PKG
from pipx import paths, pipx_metadata_file
from pipx.backends import UV, Backend
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import PipxError, get_venv_paths, redact_url_credentials
from pipx.venv import Venv, reset_backend_override_warnings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from pipx.constants import ExitCode


@pytest.fixture
def venv_with_site_packages(tmp_path: Path, mocker: MockerFixture) -> tuple[Venv, tuple[Path, Path], MagicMock]:
    venv: Final[Venv] = Venv(tmp_path / "demo")
    venv.python_path.parent.mkdir(parents=True)
    venv.python_path.touch()
    purelib: Final[Path] = venv.root / "purelib"
    platlib: Final[Path] = venv.root / "platlib"

    purelib_demo: Final[Path] = purelib / "demo-1.0.dist-info"
    purelib_demo.mkdir(parents=True)
    (purelib_demo / "METADATA").write_text("Name: demo\nVersion: 1.0\n", encoding="utf-8")

    platlib_demo: Final[Path] = platlib / "demo2-1.0.dist-info"
    platlib_demo.mkdir(parents=True)
    (platlib_demo / "METADATA").write_text("Name: demo2\nVersion: 1.0\n", encoding="utf-8")

    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.util.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{purelib}\n{platlib}\n", stderr=""),
    )
    return venv, (purelib_demo, platlib_demo), run_subprocess


def test_has_package(venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock]) -> None:
    venv, _, _ = venv_with_site_packages
    assert (venv.has_package("demo"), venv.has_package("demo2")) == (True, True)


def test_has_app_caches_site_packages(venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock]) -> None:
    venv, (purelib_demo, _), run_subprocess = venv_with_site_packages
    (purelib_demo / "entry_points.txt").write_text("[pipx.run]\ndemo = demo:main\n", encoding="utf-8")

    assert (venv.has_app("demo", "demo"), venv.has_app("demo", "demo"), run_subprocess.call_count) == (True, True, 1)


def test_run_app_rejects_python_args_without_entry_point(
    venv_with_site_packages: tuple[Venv, tuple[Path, Path], MagicMock],
) -> None:
    venv, _, _ = venv_with_site_packages

    with pytest.raises(PipxError, match="'demo' is not a Python entry point"):
        venv.run_app("demo", "demo", [], python_args=["-b"])


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
def test_install_records_the_venv_python_version(backend: str) -> None:
    assert not run_pipx_cli(["install", "--backend", backend, "pycowsay"])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").python_version == f"Python {platform.python_version()}"


_CREDENTIALED_REQUIREMENT: Final[str] = "helper @ http://u:s3cr3ttok@127.0.0.1:9/helper-1.0-py3-none-any.whl"


def test_install_unmanaged_packages_error_hides_url_credentials(venv_failing_install: Venv) -> None:
    with pytest.raises(PipxError) as error:
        venv_failing_install.install_unmanaged_packages([_CREDENTIALED_REQUIREMENT], [], cooldown_days=None)

    assert (
        " ".join(str(error.value).split()) == f"Error installing {redact_url_credentials(_CREDENTIALED_REQUIREMENT)}."
    )


@pytest.fixture
def venv_failing_install(tmp_path: Path, mocker: MockerFixture) -> Venv:
    (root := tmp_path / "demo").mkdir()
    (root / "pyvenv.cfg").touch()
    venv: Final[Venv] = Venv(root)
    mocker.patch.object(venv.backend, "install", autospec=True, return_value=subprocess.CompletedProcess([], 1, "", ""))
    return venv


def test_install_unmanaged_packages_logs_without_url_credentials(
    venv_failing_install: Venv, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"), pytest.raises(PipxError):
        venv_failing_install.install_unmanaged_packages([_CREDENTIALED_REQUIREMENT], [], cooldown_days=None)

    assert f"Installing {redact_url_credentials(_CREDENTIALED_REQUIREMENT)}" in caplog.messages


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda venv: venv.list_installed_packages(), id="list"),
        pytest.param(lambda venv: venv.uninstall_packages("demo"), id="uninstall"),
        pytest.param(lambda venv: venv.run_pip_get_exit_code(["install", "demo"]), id="runpip"),
        pytest.param(
            lambda venv: venv.upgrade_package(
                "demo",
                "demo",
                [],
                include_dependencies=False,
                include_resources_from=[],
                include_apps=True,
                is_main_package=True,
                suffix="",
                expected_apps=None,
                cooldown_days=None,
            ),
            id="upgrade",
        ),
    ],
)
def test_venv_without_pyvenv_cfg_refuses_installer(
    operation: Callable[[Venv], set[str] | ExitCode | None], tmp_path: Path, mocker: MockerFixture
) -> None:
    backend: Final[MagicMock] = mocker.create_autospec(Backend, instance=True)
    mocker.patch("pipx.venv.get_backend", autospec=True, return_value=backend)
    venv: Final[Venv] = Venv(tmp_path / "demo")

    with pytest.raises(PipxError, match=r"has no pyvenv\.cfg, so it is no longer a virtual environment"):
        operation(venv)

    assert backend.method_calls == []


@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_refuses_venv_without_pyvenv_cfg(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    # a wheel's data file can own pyvenv.cfg, and upgrading to a release without it deletes the file
    (paths.CTX.venvs / "pycowsay" / "pyvenv.cfg").unlink()
    capsys.readouterr()

    assert (run_pipx_cli(["runpip", "pycowsay", "list"]), "pipx reinstall pycowsay" in capsys.readouterr().err) == (
        1,
        True,
    )


def test_backend_override_warning_dedups_per_venv(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # `upgrade-all --backend uv` over many pip-backed venvs would otherwise log a multi-line block per Venv
    (venv_dir := tmp_path / "demo").mkdir()
    metadata_payload: Final[CurrentMetadata] = {
        "main_package": LEGACY_MAIN_PACKAGE,
        "python_version": "3.12",
        "source_interpreter": None,
        "venv_args": [],
        "injected_packages": {},
        "backend": "pip",
        "pipx_metadata_version": "0.6",
    }
    (venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).write_text(json.dumps(metadata_payload))
    reset_backend_override_warnings()
    caplog.set_level("WARNING", logger="pipx.venv")

    Venv(venv_dir, backend="uv")
    Venv(venv_dir, backend="uv")
    Venv(venv_dir, backend="uv")

    assert len([rec for rec in caplog.records if "Ignoring --backend=uv" in rec.message]) == 1


@pytest.mark.parametrize(
    ("backend", "env_backend", "expected"),
    [
        pytest.param("uv", None, (UV, "cli"), id="cli"),
        pytest.param(None, "uv", (UV, "env"), id="env"),
    ],
)
def test_venv_without_record_resolves_like_a_fresh_one(
    tmp_path: Path, backend: str | None, env_backend: str | None, expected: tuple[str, str]
) -> None:
    (venv_dir := tmp_path / "demo").mkdir()
    (venv_dir / "pyvenv.cfg").touch()

    venv: Final[Venv] = Venv(venv_dir, backend=backend, env_backend=env_backend)

    assert (venv.backend_name, venv.backend_source) == expected


def test_package_name_determination_preserves_install_error(mocker: MockerFixture, tmp_path: Path) -> None:
    (tmp_path / "pyvenv.cfg").touch()
    venv: Final[Venv] = Venv(tmp_path)
    backend: Final[MagicMock] = mocker.create_autospec(Backend, instance=True)
    # Python before 3.14 ignores a keyword argument naming a method of an autospec
    backend.cooldown_args.return_value = []
    backend.install.return_value = subprocess.CompletedProcess(
        ["pip", "install", "requires-newer-python"],
        1,
        stdout="",
        stderr="ERROR: Package 'requires-newer-python' requires a different Python\n",
    )
    mocker.patch.object(venv, "_backend", backend)
    mocker.patch.object(venv, "list_installed_packages", return_value=set())
    mocker.patch("pipx.venv.get_site_packages", return_value=[])

    with pytest.raises(PipxError) as excinfo:
        venv.install_package_no_deps("requires-newer-python", [], None)

    error: Final[str] = str(excinfo.value)
    assert ("requires a different Python" in error, "Cannot determine package name from spec" in error) == (
        True,
        False,
    )


@pytest.mark.parametrize(
    "dist_info_dirs",
    [
        pytest.param(["cooltool-1.0.dist-info"], id="rewritten-metadata"),
        pytest.param(["cooltool-1.0.dist-info", "blacken-9.0.dist-info"], id="added-distribution"),
    ],
)
def test_package_name_determination_rejects_name_not_matching_dist_info(
    mocker: MockerFixture, tmp_path: Path, dist_info_dirs: list[str]
) -> None:
    venv: Final[Venv] = _probe_venv(mocker, tmp_path, "blacken", dist_info_dirs)

    with pytest.raises(PipxError, match=r"declares\s+the\s+name\s+'blacken'"):
        venv.install_package_no_deps("https://example.com/cooltool-1.0-py3-none-any.whl", [], None)


def _probe_venv(mocker: MockerFixture, site_packages: Path, listed_name: str, dist_info_dirs: list[str]) -> Venv:
    def install(**_kwargs: object) -> subprocess.CompletedProcess[str]:
        for dist_info_dir in dist_info_dirs:
            (site_packages / dist_info_dir).mkdir()
        return subprocess.CompletedProcess(["pip", "install"], 0, stdout="", stderr="")

    (root := site_packages / "probe-venv").mkdir()
    (root / "pyvenv.cfg").touch()
    venv: Final[Venv] = Venv(root)
    backend: Final[MagicMock] = mocker.create_autospec(Backend, instance=True, **{"cooldown_args.return_value": []})
    # Python 3.11's create_autospec drops a side_effect passed as a keyword for a child method
    backend.install.side_effect = install
    mocker.patch.object(venv, "_backend", backend)
    mocker.patch.object(venv, "list_installed_packages", side_effect=[{"pip"}, {"pip", listed_name}])
    mocker.patch("pipx.venv.get_site_packages", return_value=[site_packages])
    return venv


def test_package_name_determination_accepts_normalized_dist_info_name(mocker: MockerFixture, tmp_path: Path) -> None:
    venv: Final[Venv] = _probe_venv(mocker, tmp_path, "Cool.Tool", ["cool_tool-1.0.dist-info"])

    assert venv.install_package_no_deps("https://example.com/cool_tool-1.0-py3-none-any.whl", [], None) == "Cool.Tool"


@pytest.mark.parametrize(
    "symlinks",
    [
        pytest.param(
            True, id="symlinks", marks=pytest.mark.skipif(sys.platform == "win32", reason="venv copies on Windows")
        ),
        pytest.param(False, id="copies"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_from_bootstrap_venv_records_interpreter_outside_it(tmp_path: Path, symlinks: bool) -> None:
    EnvBuilder(symlinks=symlinks).create(bootstrap := tmp_path / "bootstrap")
    _, bootstrap_python, _ = get_venv_paths(bootstrap)

    assert not run_pipx_cli(["install", "--python", str(bootstrap_python), PKG["pycowsay"]["spec"]])

    recorded: Final[Path | None] = PipxMetadata(paths.CTX.venvs / "pycowsay").source_interpreter
    assert recorded is not None
    assert (recorded.is_file(), recorded.is_relative_to(bootstrap)) == (True, False)
