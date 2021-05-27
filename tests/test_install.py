import os
import re
import sys
from pathlib import Path
from unittest import mock

import pytest  # type: ignore

from helpers import app_name, run_pipx_cli, unwrap_log_text
from package_info import PKG
from pipx import constants

TEST_DATA_PATH = "./testdata/test_package_specifier"


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        run_pipx_cli(["install", "--help"])
    captured = capsys.readouterr()
    assert "apps you can run from anywhere" in captured.out


def install_package(capsys, pipx_temp_env, caplog, package, package_name=""):
    if not package_name:
        package_name = package

    run_pipx_cli(["install", package, "--verbose"])
    captured = capsys.readouterr()
    assert f"installed package {package_name}" in captured.out
    if not sys.platform.startswith("win"):
        # TODO assert on windows too
        # https://github.com/pypa/pipx/issues/217
        assert "symlink missing or pointing to unexpected location" not in captured.out
    assert "not modifying" not in captured.out
    assert "is not on your PATH environment variable" not in captured.out
    assert "⚠️" not in caplog.text
    assert "WARNING" not in caplog.text


@pytest.mark.parametrize(
    "package_name, package_spec",
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
def test_install_easy_packages(
    capsys, pipx_temp_env, caplog, package_name, package_spec
):
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("cloudtoken", PKG["cloudtoken"]["spec"]),
        ("awscli", PKG["awscli"]["spec"]),
        ("ansible", PKG["ansible"]["spec"]),
        ("shell-functools", PKG["shell-functools"]["spec"]),
    ],
)
def test_install_tricky_packages(
    capsys, pipx_temp_env, caplog, package_name, package_spec
):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")
    if sys.platform.startswith("win") and package_name == "ansible":
        pytest.skip("Ansible is not installable on Windows")

    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


# TODO: Add git+... spec when git is in binpath of tests (Issue #303)
@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        # ("nox", "git+https://github.com/cs01/nox.git@5ea70723e9e6"),
        ("pylint", PKG["pylint"]["spec"]),
        ("black", "https://github.com/ambv/black/archive/18.9b0.zip"),
    ],
)
def test_install_package_specs(
    capsys, pipx_temp_env, caplog, package_name, package_spec
):
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


def test_force_install(pipx_temp_env, capsys):
    run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # print(captured.out)
    assert "installed package" in captured.out

    run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "installed package" not in captured.out
    assert "'pycowsay' already seems to be installed" in captured.out

    run_pipx_cli(["install", "pycowsay", "--force"])
    captured = capsys.readouterr()
    assert "Installing to existing venv" in captured.out


def test_install_no_packages_found(pipx_temp_env, capsys):
    run_pipx_cli(["install", PKG["pygdbmi"]["spec"]])
    captured = capsys.readouterr()
    assert "No apps associated with package pygdbmi" in captured.err


def test_install_same_package_twice_no_force(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert (
        "'pycowsay' already seems to be installed. Not modifying existing installation"
        in captured.out
    )


def test_include_deps(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", PKG["jupyter"]["spec"]]) == 1
    assert not run_pipx_cli(["install", PKG["jupyter"]["spec"], "--include-deps"])


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("jaraco-financial", "jaraco.financial==2.0.0"),
        ("tox-ini-fmt", PKG["tox-ini-fmt"]["spec"]),
    ],
)
def test_name_tricky_characters(
    caplog, capsys, pipx_temp_env, package_name, package_spec
):
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


def test_extra(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "nox[tox_to_nox]==2020.8.22", "--include-deps"])
    captured = capsys.readouterr()
    assert f"- {app_name('tox')}\n" in captured.out


def test_install_local_extra(pipx_temp_env, capsys):
    assert not run_pipx_cli(
        ["install", TEST_DATA_PATH + "/local_extras[cow]", "--include-deps"]
    )
    captured = capsys.readouterr()
    assert f"- {app_name('pycowsay')}\n" in captured.out


def test_path_warning(pipx_temp_env, capsys, monkeypatch, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "is not on your PATH environment variable" not in unwrap_log_text(
        caplog.text
    )

    monkeypatch.setenv("PATH", "")
    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    assert "is not on your PATH environment variable" in unwrap_log_text(caplog.text)


def test_existing_symlink_points_to_existing_wrong_location_warning(
    pipx_temp_env, caplog, capsys
):
    if sys.platform.startswith("win"):
        pytest.skip("pipx does not use symlinks on Windows")

    constants.LOCAL_BIN_DIR.mkdir(exist_ok=True, parents=True)
    (constants.LOCAL_BIN_DIR / "pycowsay").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in unwrap_log_text(caplog.text)
    assert "symlink missing or pointing to unexpected location" in captured.out
    # bin dir was on path, so the warning should NOT appear (even though the symlink
    # pointed to the wrong location)
    assert "is not on your PATH environment variable" not in captured.err


def test_existing_symlink_points_to_nothing(pipx_temp_env, capsys):
    if sys.platform.startswith("win"):
        pytest.skip("pipx does not use symlinks on Windows")

    constants.LOCAL_BIN_DIR.mkdir(exist_ok=True, parents=True)
    (constants.LOCAL_BIN_DIR / "pycowsay").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


def test_pip_args_forwarded_to_package_name_determination(pipx_temp_env, capsys):
    assert run_pipx_cli(
        [
            "install",
            # use a valid spec and invalid pip args
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "--verbose",
            "--pip-args='--asdf'",
        ]
    )
    captured = capsys.readouterr()
    assert "Cannot determine package name from spec" in captured.err


def test_install_suffix(pipx_temp_env, capsys):
    name = "pbr"

    suffix = "_a"
    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_a = app_name(f"{name}{suffix}")
    assert f"- {name_a}" in captured.out

    suffix = "_b"
    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_b = app_name(f"{name}{suffix}")
    assert f"- {name_b}" in captured.out

    assert (constants.LOCAL_BIN_DIR / name_a).exists()
    assert (constants.LOCAL_BIN_DIR / name_b).exists()


def test_install_pip_failure(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", "weblate==4.3.1", "--verbose"])
    captured = capsys.readouterr()

    assert "Fatal error from pip" in captured.err

    pip_log_file_match = re.search(
        r"Full pip output in file:\s+(\S.+)$", captured.err, re.MULTILINE
    )
    assert pip_log_file_match
    assert Path(pip_log_file_match.group(1)).exists()

    assert re.search(r"pip (failed|seemed to fail) to build package", captured.err)
