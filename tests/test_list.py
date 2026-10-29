from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from filelock import BaseFileLock

from helpers import (
    SKIP_IF_WINDOWS,
    app_name,
    assert_package_metadata,
    create_package_info_ref,
    mock_legacy_venv,
    pipx_subprocess_env,
    remove_venv_interpreter,
    run_pipx_cli,
)
from package_info import PKG
from pipx import constants, paths, shared_libs, venv
from pipx.commands import common
from pipx.commands.list_packages import list_packages
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, load_spec_file
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["list"])
    assert "nothing has been installed with pipx" in capsys.readouterr().err


@SKIP_IF_WINDOWS
@pytest.mark.skipif(not constants.WINDOWS and os.geteuid() == 0, reason="root reads files whatever their mode")
@pytest.mark.parametrize(
    ("flags", "listed"),
    [
        pytest.param([], "package black", id="text"),
        pytest.param(["--short"], "black ", id="short"),
        pytest.param(["--json"], '"black"', id="json"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_reports_unreadable_metadata_per_environment(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture, flags: list[str], listed: str
) -> None:
    assert not run_pipx_cli(["install", "pycowsay", PKG["black"]["spec"]])
    (paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME).chmod(0)
    capsys.readouterr()
    caplog.clear()

    assert (
        run_pipx_cli(["list", *flags]),
        listed in capsys.readouterr().out,
        "package pycowsay has pipx metadata this user cannot read" in caplog.text,
        "missing internal pipx metadata" in caplog.text,
    ) == (constants.EXIT_CODE_LIST_PROBLEM, True, True, False)


def test_list_allows_read_only_venv_lock(tmp_path: Path, mocker: MockerFixture) -> None:
    (venv_dir := tmp_path / "venvs" / "example").mkdir(parents=True)
    venv_container: Final[venv.VenvContainer] = venv.VenvContainer(venv_dir.parent)
    lock: Final = mocker.create_autospec(BaseFileLock, instance=True)
    # Python before 3.14 ignores a keyword argument naming a method of an autospec
    lock.acquire.side_effect = PermissionError("read-only lock file")
    mocker.patch.object(venv_container, "venv_lock", return_value=lock)
    mocker.patch.object(
        importlib.import_module("pipx.commands.list_packages"),
        "get_venv_summary",
        return_value=("package example 1", common.VenvProblems()),
    )

    assert not list_packages(
        venv_container,
        [venv_dir],
        include_injected=False,
        json_format=False,
        short_format=False,
        pinned_only=False,
    )

    lock.release.assert_not_called()


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_global(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "installed package" in capsys.readouterr().out

    assert not run_pipx_cli(["list", "--global"])
    assert "nothing has been installed with pipx" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_missing_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["list"])
    assert "package pycowsay has invalid interpreter" not in capsys.readouterr().err

    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["list"])
    assert "package pycowsay has invalid interpreter" in capsys.readouterr().err


@pytest.mark.usefixtures("uv_symlinked_install")
def test_list_counts_link_to_uv_symlinked_man_page_as_exposed(capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()

    assert not run_pipx_cli(["list"])

    assert f"    - {Path('man1', 'tool.1')}\n" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    suffix: Final[str] = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["list"])
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_legacy_venv_without_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=None)

    assert run_pipx_cli(["list"])
    assert "package pycowsay has missing internal pipx metadata" in capsys.readouterr().err


@pytest.mark.parametrize("metadata_version", ["0.1", "0.2", "0.3"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_legacy_venv(capsys: pytest.CaptureFixture[str], metadata_version: str) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    assert "package pycowsay 0.0.0.2," in capsys.readouterr().out


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
    (venv_dir := paths.CTX.venvs / "broken").mkdir(parents=True)
    (venv_dir / PIPX_INFO_FILENAME).write_text(metadata, encoding="utf-8")
    assert run_pipx_cli(["list"]) == constants.EXIT_CODE_LIST_PROBLEM


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_suffix_legacy_venv(capsys: pytest.CaptureFixture[str], metadata_version: str) -> None:
    suffix: Final[str] = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    captured: Final = capsys.readouterr()
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in captured.out
    assert f"shell completions are exposed at {paths.CTX.completion_dir}" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    pipx_venvs_dir: Final[Path] = paths.CTX.home / "venvs"
    venv_bin_dir: Final[str] = "Scripts" if constants.WINDOWS else "bin"

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--output", "json"])
    captured: Final = capsys.readouterr()

    assert not re.search(r"\S", captured.err)
    (listed := tmp_path / "list.json").write_text(captured.out, encoding="utf-8")
    json_parsed: Final = load_spec_file(listed)

    assert sorted(json_parsed["venvs"].keys()) == ["pycowsay", "pylint"]

    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pycowsay"]["metadata"]["main_package"]),
        create_package_info_ref("pycowsay", "pycowsay", pipx_venvs_dir),
    )
    assert json_parsed["venvs"]["pycowsay"]["metadata"]["injected_packages"] == {}

    pylint_package_ref: Final[PackageInfo] = create_package_info_ref(
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
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["black"]),
        create_package_info_ref("pylint", "black", pipx_venvs_dir, include_apps=False),
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_short(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])
    captured: Final = capsys.readouterr()

    assert "pycowsay 0.0.0.2" in captured.out
    assert "isort 5.6.4" in captured.out


@pytest.mark.parametrize("option", [pytest.param("--short", id="short"), pytest.param("--pinned", id="pinned")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_json_rejects_human_filter(
    capsys: pytest.CaptureFixture[str],
    option: str,
) -> None:
    assert run_pipx_cli(["list", "--output", "json", option]) == 1

    document: Final = json.loads(capsys.readouterr().out)
    assert document["status"] == "error"
    assert "--output json cannot be combined with --short or --pinned" in document["errors"][0]["message"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay"])

    captured: Final = capsys.readouterr()
    assert ("package pycowsay 0.0.0.2," in captured.out, "package isort" in captured.out) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_packages_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay", "isort", "--json"])

    assert sorted(json.loads(capsys.readouterr().out)["venvs"]) == ["isort", "pycowsay"]


@pytest.mark.parametrize(
    "packages",
    [
        pytest.param(["isort"], id="single"),
        pytest.param(["isort", "isort"], id="repeated"),
        pytest.param(["isort", "ISort"], id="mixed-case"),
        pytest.param(["isort", "isort==5.6.4"], id="with-specifier"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_short(
    capsys: pytest.CaptureFixture[str],
    packages: list[str],
) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["list", *packages, "--short"])

    assert capsys.readouterr().out == "isort 5.6.4\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_with_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"], "--suffix=@1"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "pycowsay@1", "--short"])

    assert capsys.readouterr().out == "pycowsay 0.0.0.2\n"


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_selected_package_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    assert not run_pipx_cli(["pin", "isort"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "isort", "--pinned"])

    assert capsys.readouterr().out == "isort 5.6.4\n"


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
    assert not run_pipx_cli(["inject", "pycowsay", PKG["isort"]["spec"], "--include-apps"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--include-injected"])

    assert f"    - {PKG['isort']['apps'][0]}" in capsys.readouterr().out.splitlines()


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_waits_for_install(tmp_path: Path) -> None:
    release: Final[Path] = tmp_path / "release"
    with _install_paused_under_lock(tmp_path, "slow-app", release) as install:
        listed: Final[subprocess.Popen[str]] = _start_pipx("list", "--short")
        # the install cannot progress until release, so a list that honours the lock is still running
        with pytest.raises(subprocess.TimeoutExpired):
            listed.wait(timeout=1)
        release.touch()
        install_stdout, install_stderr = install.communicate()
        listed_stdout, listed_stderr = listed.communicate()

    assert (install.returncode, listed.returncode, listed_stdout.strip()) == (0, 0, "slow-app 1"), (
        install_stdout,
        install_stderr,
        listed_stdout,
        listed_stderr,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_does_not_wait_for_other_environment(tmp_path: Path) -> None:
    with _install_paused_under_lock(tmp_path, "blocked-app", tmp_path / "release") as blocked_install:
        installed: Final[subprocess.CompletedProcess[str]] = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipx",
                "install",
                str(_create_wheel(tmp_path, "other-app")),
                "--skip-maintenance",
            ],
            env=pipx_subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        blocked_returncode: Final[int | None] = blocked_install.poll()

    assert (installed.returncode, blocked_returncode, (paths.CTX.venvs / "other-app").is_dir()) == (0, None, True), (
        installed.stdout,
        installed.stderr,
    )


@pytest.mark.usefixtures("pipx_temp_env", "mocked_github_api")
def test_list_standalone_interpreter(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    assert not run_pipx_cli([
        "install",
        "--fetch-python=missing",
        "--python",
        f"{sys.version_info.major}.{sys.version_info.minor}",
        PKG["pycowsay"]["spec"],
    ])
    capsys.readouterr()

    assert not run_pipx_cli(["list"])

    assert "standalone" in capsys.readouterr().out


@pytest.mark.parametrize(
    "flags",
    [
        pytest.param([], id="default"),
        pytest.param(["--skip-maintenance"], id="skip-maintenance"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_list_does_not_trigger_maintenance(flags: list[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    now: Final[float] = time.time()
    shared_libs.SHARED_LIBS.create(verbose=True, pip_args=[])
    shared_libs.SHARED_LIBS.has_been_updated_this_run = False
    os.utime(shared_libs.SHARED_LIBS.pip_path, (now, -shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60 + now))
    assert shared_libs.SHARED_LIBS.needs_upgrade

    run_pipx_cli(["list", *flags])

    assert (shared_libs.SHARED_LIBS.has_been_updated_this_run, shared_libs.SHARED_LIBS.needs_upgrade) == (False, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_pinned_packages(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["list", "--pinned"])

    captured: Final = capsys.readouterr()
    assert "black 22.8.0" in captured.out
    assert "pycowsay 0.0.0.2" not in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_list_pinned_packages_include_injected(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["isort"]["spec"], PKG["nox"]["spec"]])
    assert not run_pipx_cli(["inject", "isort", PKG["black"]["spec"]])

    assert not run_pipx_cli(["pin", "isort"])
    assert not run_pipx_cli(["pin", "nox"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--pinned", "--include-injected"])

    captured: Final = capsys.readouterr()

    assert "nox 2023.4.22" in captured.out
    assert "isort 5.6.4" in captured.out
    assert "black 22.8.0 (injected in venv isort)" in captured.out


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_list_installed_packages_error(tmp_path: Path, fake_process: FakeProcess) -> None:
    (tmp_path / "fake_venv").mkdir()
    (tmp_path / "fake_venv" / "pyvenv.cfg").touch()
    fake_venv: Final[venv.Venv] = venv.Venv(tmp_path / "fake_venv")
    shared_python: Final[Path] = shared_libs.SHARED_LIBS.python_path
    shared_python.parent.mkdir(parents=True)
    shared_python.touch()

    fake_process.register(
        [str(fake_venv.python_path), "-m", "pip", "list", "--format=json"], returncode=1, stderr="unit test stderr"
    )
    fake_process.register([str(shared_python), "-c", "from pip._internal.cli.main import main"])

    with pytest.raises(PipxError) as excinfo:
        fake_venv.list_installed_packages()

    # pipx_wrap breaks the message into lines on render
    rendered: Final[str] = " ".join(str(excinfo.value).split())
    assert "Failed to execute" in rendered
    assert "Process exited with return code 1" in rendered
    assert "unit test stderr" in rendered


@contextmanager
def _install_paused_under_lock(
    tmp_path: Path, name: str, release: Path
) -> Generator[subprocess.Popen[str], None, None]:
    entered: Final[Path] = tmp_path / f"{name}-entered"
    # the wheel's .pth imports its module whenever the environment's python starts, and pipx starts it to inspect the
    # new environment while holding the lock
    pause: Final[str] = (
        "from pathlib import Path\n"
        "from time import sleep\n"
        f"Path({str(entered)!r}).touch()\n"
        f"while not Path({str(release)!r}).exists():\n"
        "    sleep(0.01)\n"
    )
    install: Final[subprocess.Popen[str]] = _start_pipx(
        "install", str(_create_wheel(tmp_path, name, pause)), "--skip-maintenance"
    )
    try:
        while not entered.exists():
            if install.poll() is not None:
                pytest.fail(f"install exited before pausing under its lock: {install.communicate()!r}")
            time.sleep(0.01)
        yield install
    finally:
        release.touch()
        if install.returncode is None:
            install.communicate()


def _create_wheel(tmp_path: Path, name: str, module_prefix: str = "") -> Path:
    # a prebuilt wheel skips the isolated build a project directory needs, which takes seconds on Windows
    module: Final[str] = name.replace("-", "_")
    dist_info: Final[str] = f"{module}-1.dist-info"
    with zipfile.ZipFile(wheel := tmp_path / f"{module}-1-py3-none-any.whl", "w") as archive:
        for path, content in {
            f"{module}.py": f"{module_prefix}def main() -> None:\n    print({name!r})\n",
            f"{module}.pth": f"import {module}\n",
            f"{dist_info}/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: 1\n",
            f"{dist_info}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            f"{dist_info}/entry_points.txt": f"[console_scripts]\n{name} = {module}:main\n",
            f"{dist_info}/RECORD": "",
        }.items():
            archive.writestr(path, content)
    return wheel


def _start_pipx(*args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "pipx", *args],
        env=pipx_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
