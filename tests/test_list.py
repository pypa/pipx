from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Final

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    assert_package_metadata,
    create_package_info_ref,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    skip_if_windows,
)
from package_info import PKG
from pipx import constants, paths, shared_libs, venv
from pipx.commands import common
from pipx.pipx_metadata_file import (
    PIPX_INFO_FILENAME,
    PackageInfo,
    _json_decoder_object_hook,  # noqa: PLC2701  # the decode hook has no public re-export
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

_COMMAND_TIMEOUT: Final[int] = 30


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.err


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_global(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package" in captured.out

    assert not run_pipx_cli(["list", "--global"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_missing_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" not in captured.err

    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in captured.out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_legacy_venv(capsys: pytest.CaptureFixture[str], metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    if metadata_version is None:
        assert run_pipx_cli(["list"])
        captured = capsys.readouterr()
        assert "package pycowsay has missing internal pipx metadata" in captured.err
    else:
        assert not run_pipx_cli(["list"])
        captured = capsys.readouterr()
        assert "package pycowsay 0.0.0.2," in captured.out


@pytest.mark.parametrize(
    "metadata",
    [
        pytest.param("{", id="invalid-json"),
        pytest.param("{}", id="missing-version"),
        pytest.param(
            '{"pipx_metadata_version":"0.6","main_package":{"unexpected":true}}',
            id="unexpected-package-field",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_returns_problem_for_corrupt_metadata(metadata: str) -> None:
    venv_dir = paths.ctx.venvs / "broken"
    venv_dir.mkdir(parents=True)
    (venv_dir / PIPX_INFO_FILENAME).write_text(metadata, encoding="utf-8")
    assert run_pipx_cli(["list"]) == constants.EXIT_CODE_LIST_PROBLEM


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_suffix_legacy_venv(capsys: pytest.CaptureFixture[str], metadata_version: str) -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in captured.out
    assert f"shell completions are exposed at {paths.ctx.completion_dir}" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    pipx_venvs_dir = paths.ctx.home / "venvs"
    venv_bin_dir = "Scripts" if constants.WINDOWS else "bin"

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--output", "json"])
    captured = capsys.readouterr()

    assert not re.search(r"\S", captured.err)
    json_parsed = json.loads(captured.out, object_hook=_json_decoder_object_hook)

    # raises error if not valid json
    assert sorted(json_parsed["venvs"].keys()) == ["pycowsay", "pylint"]

    # pycowsay venv
    pycowsay_package_ref = create_package_info_ref("pycowsay", "pycowsay", pipx_venvs_dir)
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pycowsay"]["metadata"]["main_package"]),
        pycowsay_package_ref,
    )
    assert json_parsed["venvs"]["pycowsay"]["metadata"]["injected_packages"] == {}

    # pylint venv
    pylint_package_ref = create_package_info_ref(
        "pylint",
        "pylint",
        pipx_venvs_dir,
        app_paths_of_dependencies={
            "dill": [
                pipx_venvs_dir / "pylint" / venv_bin_dir / "get_gprof",
                pipx_venvs_dir / "pylint" / venv_bin_dir / "get_objgraph",
                pipx_venvs_dir / "pylint" / venv_bin_dir / "undill",
            ],
            "isort": [
                pipx_venvs_dir / "pylint" / venv_bin_dir / app_name("isort"),
                pipx_venvs_dir / "pylint" / venv_bin_dir / app_name("isort-identify-imports"),
            ],
        },
    )
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["main_package"]),
        pylint_package_ref,
    )
    assert sorted(json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"].keys()) == ["black"]
    black_package_ref = create_package_info_ref("pylint", "black", pipx_venvs_dir, include_apps=False)
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["black"]),
        black_package_ref,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_short(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])
    captured = capsys.readouterr()

    assert "pycowsay 0.0.0.2" in captured.out
    assert "pylint 3.0.4" in captured.out


@pytest.mark.parametrize("option", [pytest.param("--short", id="short"), pytest.param("--pinned", id="pinned")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_json_rejects_human_filter(
    capsys: pytest.CaptureFixture[str],
    option: str,
) -> None:
    assert run_pipx_cli(["list", "--output", "json", option]) == 1

    document = json.loads(capsys.readouterr().out)
    assert document["status"] == "error"
    assert "--output json cannot be combined with --short or --pinned" in document["errors"][0]["message"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay"])

    captured = capsys.readouterr()
    assert ("package pycowsay 0.0.0.2," in captured.out, "package pylint" in captured.out) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_packages_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay", "pylint", "--json"])

    assert sorted(json.loads(capsys.readouterr().out)["venvs"]) == ["pycowsay", "pylint"]


@pytest.mark.parametrize(
    "packages",
    [
        pytest.param(["pylint"], id="single"),
        pytest.param(["pylint", "pylint"], id="repeated"),
        pytest.param(["pylint", "PyLint"], id="mixed-case"),
        pytest.param(["pylint", "pylint==3.0.4"], id="with-specifier"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_short(
    capsys: pytest.CaptureFixture[str],
    packages: list[str],
) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", *packages, "--short"])

    assert capsys.readouterr().out == "pylint 3.0.4\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_with_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay@1", "--short"])

    assert capsys.readouterr().out == "pycowsay 0.0.0.2\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["pin", "pylint"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pylint", "--pinned"])

    assert capsys.readouterr().out == "pylint 3.0.4\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_rejects_missing_selected_package(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["list", "missing"])
    assert capsys.readouterr().err.endswith("venv for 'missing' was not found. Was 'missing' installed with pipx?\n")


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_injected_apps_without_symlinks(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["pylint"]["spec"], "--include-apps"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--include-injected"])

    assert f"    - {PKG['pylint']['apps'][0]}" in capsys.readouterr().out.splitlines()


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_waits_for_install(tmp_path: Path) -> None:
    package_dir = _create_package(tmp_path, "slow-app", "from time import sleep\nsleep(1)\n")
    install = _start_install(package_dir)
    try:
        _wait_for_path(paths.ctx.venvs / "slow-app", install)
        listed = subprocess.run(
            [sys.executable, "-m", "pipx", "list", "--short"],
            env=_subprocess_env(),
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT,
            check=False,
        )
        install_stdout, install_stderr = install.communicate(timeout=_COMMAND_TIMEOUT)
    finally:
        _stop_process(install)

    assert (install.returncode, listed.returncode, listed.stdout.strip()) == (0, 0, "slow-app 1"), (
        install_stdout,
        install_stderr,
        listed.stdout,
        listed.stderr,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_does_not_wait_for_other_environment(tmp_path: Path) -> None:
    entered = tmp_path / "entered"
    release = tmp_path / "release"
    pause = (
        "from pathlib import Path\n"
        "from time import sleep\n"
        f"Path({str(entered)!r}).touch()\n"
        f"while not Path({str(release)!r}).exists():\n    sleep(0.01)\n"
    )
    blocked_install = _start_install(_create_package(tmp_path, "blocked-app", pause))
    try:
        _wait_for_path(entered, blocked_install)
        installed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipx",
                "install",
                str(_create_package(tmp_path, "other-app")),
                "--skip-maintenance",
            ],
            env=_subprocess_env(),
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT,
            check=False,
        )
        blocked_returncode = blocked_install.poll()
    finally:
        release.touch()
        _stop_process(blocked_install, terminate=False)

    assert (installed.returncode, blocked_returncode, (paths.ctx.venvs / "other-app").is_dir()) == (0, None, True), (
        installed.stdout,
        installed.stderr,
    )


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_list_standalone_interpreter(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def which(_name: str) -> None:
        return None

    monkeypatch.setattr(shutil, "which", which)

    major = sys.version_info.major
    minor = sys.version_info.minor
    target_python = f"{major}.{minor}"

    assert not run_pipx_cli([
        "install",
        "--fetch-python=missing",
        "--python",
        target_python,
        PKG["pycowsay"]["spec"],
    ])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()

    assert "standalone" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_does_not_trigger_maintenance() -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])

    now = time.time()
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False

    access_time = now  # this can be anything
    os.utime(
        shared_libs.shared_libs.pip_path,
        (access_time, -shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60 + now),
    )
    assert shared_libs.shared_libs.needs_upgrade
    run_pipx_cli(["list"])
    assert not shared_libs.shared_libs.has_been_updated_this_run
    assert shared_libs.shared_libs.needs_upgrade

    os.utime(
        shared_libs.shared_libs.pip_path,
        (access_time, -shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60 + now),
    )
    shared_libs.shared_libs.has_been_updated_this_run = False
    assert shared_libs.shared_libs.needs_upgrade
    run_pipx_cli(["list", "--skip-maintenance"])
    assert not shared_libs.shared_libs.has_been_updated_this_run
    assert shared_libs.shared_libs.needs_upgrade


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_pinned_packages(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["list", "--pinned"])

    captured = capsys.readouterr()
    assert "black 22.8.0" in captured.out
    assert "pycowsay 0.0.0.2" not in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_pinned_packages_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"], PKG["nox"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])

    assert not run_pipx_cli(["pin", "pylint"])
    assert not run_pipx_cli(["pin", "nox"])

    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--pinned", "--include-injected"])

    captured = capsys.readouterr()

    assert "nox 2023.4.22" in captured.out
    assert "pylint 3.0.4" in captured.out
    assert "black 22.8.0 (injected in venv pylint)" in captured.out


def test_list_installed_packages_error(tmp_path: Path, fake_process: FakeProcess) -> None:
    fake_venv = venv.Venv(tmp_path / "fake_venv")
    pip_list_args = [str(fake_venv.python_path), "-m", "pip", "list", "--format=json"]

    fake_process.register(pip_list_args, returncode=1, stderr="unit test stderr")

    with pytest.raises(PipxError) as excinfo:
        fake_venv.list_installed_packages()

    # Collapse the wrapping pipx_wrap applies on render so we can assert on substrings.
    rendered = " ".join(str(excinfo.value).split())
    assert "Failed to execute" in rendered
    assert "Process exited with return code 1" in rendered
    assert "unit test stderr" in rendered


def _create_package(tmp_path: Path, name: str, setup_prefix: str = "") -> Path:
    package_dir = tmp_path / name
    package_dir.mkdir()
    module = name.replace("-", "_")
    (package_dir / "setup.py").write_text(
        f"{setup_prefix}from setuptools import setup\n"
        f"setup(name={name!r}, version='1', py_modules=[{module!r}], "
        f"entry_points={{'console_scripts': [{f'{name}={module}:main'!r}]}})\n",
        encoding="utf-8",
    )
    (package_dir / f"{module}.py").write_text(f"def main() -> None:\n    print({name!r})\n", encoding="utf-8")
    return package_dir


def _start_install(package_dir: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "pipx", "install", str(package_dir), "--skip-maintenance"],
        env=_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _subprocess_env() -> dict[str, str]:
    return os.environ | {
        "PIPX_BIN_DIR": str(paths.ctx.bin_dir),
        "PIPX_HOME": str(paths.ctx.home),
        "PIPX_MAN_DIR": str(paths.ctx.man_dir),
        "PIPX_SHARED_LIBS": str(paths.ctx.shared_libs),
    }


def _wait_for_path(path: Path, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + _COMMAND_TIMEOUT
    while not path.exists():
        if process.poll() is not None:
            pytest.fail(f"install exited before creating {path}: {process.communicate()!r}")
        if time.monotonic() >= deadline:
            pytest.fail(f"install did not create {path} within {_COMMAND_TIMEOUT} seconds")
        time.sleep(0.01)


def _stop_process(process: subprocess.Popen[str], *, terminate: bool = True) -> None:
    if process.poll() is None and terminate:
        process.terminate()
    process.communicate(timeout=_COMMAND_TIMEOUT)
