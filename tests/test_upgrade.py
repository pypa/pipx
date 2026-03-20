import pytest  # type: ignore[import-not-found]

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    skip_if_windows,
)
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata


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


def test_upgrade_missing_interpreter(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    remove_venv_interpreter("pycowsay")

    result = run_pipx_cli(["upgrade", "pycowsay"])
    assert result != 0, "upgrade should fail when Python interpreter is missing"
    captured = capsys.readouterr()
    assert "invalid python interpreter" in captured.err
    assert "pipx reinstall-all" in captured.err


def test_upgrade_editable(pipx_temp_env, capsys, root):
    empty_project_path_as_string = (root / "testdata" / "empty_project").as_posix()
    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string, "--force"])
    assert not run_pipx_cli(["upgrade", "--editable", "empty_project"])
    captured = capsys.readouterr()
    assert "empty-project is already at latest version" in captured.out


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


def test_upgrade_with_extras(pipx_temp_env, capsys):
    """Test that upgrading a package with extras in the name works correctly.

    Regression test for https://github.com/pypa/pipx/issues/925
    """
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package pycowsay" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay[test_extra]"])
    captured = capsys.readouterr()
    assert "pycowsay is already at latest version" in captured.out
    assert "Package is not installed" not in captured.err


@pytest.mark.parametrize(
    ("upgrade_args", "expected_args", "unexpected_args"),
    [
        pytest.param([], ["--no-cache-dir"], [], id="preserves_stored"),
        pytest.param(["--pip-args=--no-deps"], ["--no-deps"], ["--no-cache-dir"], id="cli_overrides_stored"),
    ],
)
def test_upgrade_pip_args(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    upgrade_args: list[str],
    expected_args: list[str],
    unexpected_args: list[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--pip-args=--no-cache-dir"])

    assert not run_pipx_cli(["upgrade", "pycowsay", *upgrade_args])

    pipx_venvs_dir = paths.ctx.home / "venvs"
    metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    for arg in expected_args:
        assert arg in metadata.main_package.pip_args
    for arg in unexpected_args:
        assert arg not in metadata.main_package.pip_args


def test_upgrade_injected_preserves_stored_pip_args(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["inject", "pylint", PKG["black"]["spec"], "--pip-args=--no-cache-dir"])

    pipx_venvs_dir = paths.ctx.home / "venvs"
    metadata = PipxMetadata(pipx_venvs_dir / "pylint")
    assert "--no-cache-dir" in metadata.injected_packages["black"].pip_args

    assert not run_pipx_cli(["upgrade", "--include-injected", "pylint"])
    capsys.readouterr()

    metadata = PipxMetadata(pipx_venvs_dir / "pylint")
    assert "--no-cache-dir" in metadata.injected_packages["black"].pip_args
