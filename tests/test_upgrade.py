import pytest  # type: ignore[import-not-found]

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, skip_if_windows
from package_info import PKG


def test_upgrade(pipx_temp_env, capsys):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    captured = capsys.readouterr()
    assert "Package is not installed" in captured.err

    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay"])
    captured = capsys.readouterr()
    assert "pycowsay is already at latest version" in captured.out


@skip_if_windows
def test_upgrade_global(pipx_temp_env, capsys):
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
def test_upgrade_legacy_venv(pipx_temp_env, capsys, metadata_version):
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


def test_upgrade_install_missing(pipx_temp_env, capsys):
    assert not run_pipx_cli(["upgrade", "pycowsay", "--install"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out


def test_upgrade_multiple(pipx_temp_env, capsys):
    name = "pylint"
    pkg_spec = PKG[name]["spec"]
    initial_version = pkg_spec.split("==")[-1]
    assert not run_pipx_cli(["install", pkg_spec])

    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["upgrade", name, "pycowsay"])
    captured = capsys.readouterr()
    assert f"upgraded package {name} from {initial_version} to" in captured.out
    assert "pycowsay is already at latest version" in captured.out


def test_upgrade_absolute_path(pipx_temp_env, capsys, root):
    assert run_pipx_cli(["upgrade", "--verbose", str((root / "testdata" / "empty_project").resolve())])
    captured = capsys.readouterr()
    assert "Package cannot be a URL" not in captured.err
