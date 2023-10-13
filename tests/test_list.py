import json
import re

import pytest  # type: ignore

from helpers import (
    app_name,
    assert_package_metadata,
    create_package_info_ref,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
)
from package_info import PKG
from pipx import constants
from pipx.pipx_metadata_file import PackageInfo, _json_decoder_object_hook


def test_cli(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.err


def test_cli_global(pipx_temp_env, monkeypatch, capsys):
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
    assert f"package pycowsay 0.0.0.1 (pycowsay{suffix})," in captured.out


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
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
        assert "package pycowsay 0.0.0.1," in captured.out


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_list_suffix_legacy_venv(pipx_temp_env, monkeypatch, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.1 (pycowsay{suffix})," in captured.out


def test_list_json(pipx_temp_env, capsys):
    pipx_venvs_dir = constants.PIPX_DIRS.HOME / "venvs"
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
    pycowsay_package_ref = create_package_info_ref(
        "pycowsay", "pycowsay", pipx_venvs_dir
    )
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
        **{
            "app_paths_of_dependencies": {
                "isort": [pipx_venvs_dir / "pylint" / venv_bin_dir / app_name("isort")]
            }
        },
    )
    assert_package_metadata(
        PackageInfo(**json_parsed["venvs"]["pylint"]["metadata"]["main_package"]),
        pylint_package_ref,
    )
    assert sorted(
        json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"].keys()
    ) == ["isort"]
    isort_package_ref = create_package_info_ref(
        "pylint", "isort", pipx_venvs_dir, include_apps=False
    )
    print(isort_package_ref)
    print(
        PackageInfo(
            **json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["isort"]
        )
    )
    assert_package_metadata(
        PackageInfo(
            **json_parsed["venvs"]["pylint"]["metadata"]["injected_packages"]["isort"]
        ),
        isort_package_ref,
    )


def test_list_short(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    captured = capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])
    captured = capsys.readouterr()

    assert "pycowsay 0.0.0.1" in captured.out
    assert "pylint 2.3.1" in captured.out
