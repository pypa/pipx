import json
import os
import re
import shutil
import sys
import time

import pytest  # type: ignore

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
from pipx import constants, paths, shared_libs
from pipx.pipx_metadata_file import PackageInfo, _json_decoder_object_hook


def test_cli(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.err


@skip_if_windows
def test_cli_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package" in captured.out

    assert not run_pipx_cli(["--global", "list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.err


def test_missing_interpreter(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" not in captured.err

    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" in captured.err


def test_list_suffix(pipx_temp_env, monkeypatch, capsys):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in captured.out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_list_legacy_venv(pipx_temp_env, monkeypatch, capsys, metadata_version):
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


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_list_suffix_legacy_venv(pipx_temp_env, monkeypatch, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.2 (pycowsay{suffix})," in captured.out


def test_list_json(pipx_temp_env, capsys):
    pipx_venvs_dir = paths.ctx.home / "venvs"
    venv_bin_dir = "Scripts" if constants.WINDOWS else "bin"

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["isort"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--json"])
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
        **{"app_paths_of_dependencies": {"isort": [pipx_venvs_dir / "pylint" / venv_bin_dir / app_name("isort")]}},
    )
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["main_package"]),
        pylint_package_ref,
    )
    assert sorted(json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"].keys()) == ["isort"]
    isort_package_ref = create_package_info_ref("pylint", "isort", pipx_venvs_dir, include_apps=False)
    print(isort_package_ref)
    print(PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["isort"]))
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["isort"]),
        isort_package_ref,
    )


def test_list_short(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])
    captured = capsys.readouterr()

    assert "pycowsay 0.0.0.2" in captured.out
    assert "pylint 2.3.1" in captured.out


def test_list_standalone_interpreter(pipx_temp_env, monkeypatch, mocked_github_api, capsys):
    def which(name):
        return None

    monkeypatch.setattr(shutil, "which", which)

    major = sys.version_info.major
    # Minor version 3.8 is not supported for fetching standalone versions
    minor = sys.version_info.minor if sys.version_info.minor != 8 else 9
    target_python = f"{major}.{minor}"

    assert not run_pipx_cli(
        [
            "install",
            "--fetch-missing-python",
            "--python",
            target_python,
            PKG["pycowsay"]["spec"],
        ]
    )
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()

    assert "standalone" in captured.out


def test_list_does_not_trigger_maintenance(pipx_temp_env, caplog):
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

    # same test with --skip-maintenance, which is a no-op
    # we expect the same result, along with a warning
    os.utime(
        shared_libs.shared_libs.pip_path,
        (access_time, -shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60 + now),
    )
    shared_libs.shared_libs.has_been_updated_this_run = False
    assert shared_libs.shared_libs.needs_upgrade
    run_pipx_cli(["list", "--skip-maintenance"])
    assert not shared_libs.shared_libs.has_been_updated_this_run
    assert shared_libs.shared_libs.needs_upgrade
