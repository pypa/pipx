import sys

import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli
from package_info import PKG


def test_upgrade(pipx_temp_env, capsys):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])


def test_upgrade_global(pipx_temp_env, capsys):
    if sys.platform.startswith("win"):
        pytest.skip("This behavior is undefined on Windows")
    assert run_pipx_cli(["--global", "upgrade", "pycowsay"])
    assert not run_pipx_cli(["--global", "install", "pycowsay"])
    assert not run_pipx_cli(["--global", "upgrade", "pycowsay"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_upgrade_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    captured = capsys.readouterr()
    if metadata_version is None:
        assert run_pipx_cli(["upgrade", "pycowsay"])
        captured = capsys.readouterr()
        assert (
            "Not upgrading pycowsay. It has missing internal pipx metadata."
            in captured.err
        )
    else:
        assert not run_pipx_cli(["upgrade", "pycowsay"])
        captured = capsys.readouterr()


def test_upgrade_suffix(pipx_temp_env, capsys):
    name = "pycowsay"
    suffix = "_a"

    assert not run_pipx_cli(["install", name, f"--suffix={suffix}"])
    assert run_pipx_cli(["upgrade", f"{name}"])
    assert not run_pipx_cli(["upgrade", f"{name}{suffix}"])


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_upgrade_suffix_legacy_venv(pipx_temp_env, capsys, metadata_version):
    name = "pycowsay"
    suffix = "_a"

    assert not run_pipx_cli(["install", name, f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert run_pipx_cli(["upgrade", f"{name}"])
    assert not run_pipx_cli(["upgrade", f"{name}{suffix}"])


def test_upgrade_specifier(pipx_temp_env, capsys):
    name = "pylint"
    pkg_spec = PKG[name]["spec"]
    initial_version = pkg_spec.split("==")[-1]

    assert not run_pipx_cli(["install", f"{pkg_spec}"])
    assert not run_pipx_cli(["upgrade", f"{name}"])
    captured = capsys.readouterr()
    assert f"upgraded package {name} from {initial_version} to" in captured.out


def test_upgrade_include_injected(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "--include-injected", "pylint"])
    captured = capsys.readouterr()
    assert "upgraded package pylint" in captured.out
    assert "upgraded package black" in captured.out


def test_upgrade_no_include_injected(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"]])
    captured = capsys.readouterr()
    assert not run_pipx_cli(["upgrade", "pylint"])
    captured = capsys.readouterr()
    assert "upgraded package pylint" in captured.out
    assert "upgraded package black" not in captured.out
