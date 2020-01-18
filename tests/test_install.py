#!/usr/bin/env python3

import os
import sys
from unittest import mock

import pytest  # type: ignore

from helpers import assert_not_in_virtualenv, run_pipx_cli, which_python
from pipx import constants

assert_not_in_virtualenv()


PYTHON3_5 = which_python("python3.5")


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
        # https://github.com/pipxproject/pipx/issues/217
        assert "symlink missing or pointing to unexpected location" not in captured.out
    assert "not modifying" not in captured.out
    assert "is not on your PATH environment variable" not in captured.out
    for record in caplog.records:
        assert "⚠️" not in record.message
        assert "WARNING" not in record.message


@pytest.mark.parametrize("package", ["pycowsay", "black"])
def test_install_easy_packages(capsys, pipx_temp_env, caplog, package):
    install_package(capsys, pipx_temp_env, caplog, package)


@pytest.mark.parametrize(
    "package", ["cloudtoken", "awscli", "ansible", "shell-functools"]
)
def test_install_tricky_packages(capsys, pipx_temp_env, caplog, package):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")

    #if sys.platform.startswith("win"):
    #    pytest.skip("TODO make this work on Windows")
    install_package(capsys, pipx_temp_env, caplog, package)


# TODO: Add git+... spec when git is in binpath of tests (Issue #303)
@pytest.mark.parametrize(
    "package_name,package_spec",
    [
        # ("nox", "git+https://github.com/cs01/nox.git@5ea70723e9e6"),
        ("pylint", "pylint==2.3.1"),
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
    assert "Installing to existing directory" in captured.out


def test_install_no_packages_found(pipx_temp_env, capsys):
    run_pipx_cli(["install", "pygdbmi"])
    captured = capsys.readouterr()
    assert "No apps associated with package pygdbmi" in captured.err


def test_install_same_package_twice_no_error(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])


def test_include_deps(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", "jupyter==1.0.0"]) == 1
    assert not run_pipx_cli(["install", "jupyter==1.0.0", "--include-deps"])


def test_path_warning(pipx_temp_env, capsys, monkeypatch, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "is not on your PATH environment variable" not in caplog.text

    monkeypatch.setenv("PATH", "")
    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    assert "is not on your PATH environment variable" in caplog.text


def test_existing_symlink_points_to_existing_wrong_location_warning(
    pipx_temp_env, caplog, capsys
):
    if sys.platform.startswith("win"):
        pytest.skip("pipx does not use symlinks on Windows")

    constants.LOCAL_BIN_DIR.mkdir(exist_ok=True, parents=True)
    (constants.LOCAL_BIN_DIR / "pycowsay").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in caplog.text
    assert "symlink missing or pointing to unexpected location" in captured.out
    # bin dir was on path, so the warning should NOT appear (even though the symlink
    # pointed to the wrong location)
    assert "is not on your PATH environment variable" not in captured.err


def test_existing_symlink_points_to_nothing(pipx_temp_env, caplog, capsys):
    if sys.platform.startswith("win"):
        pytest.skip("pipx does not use symlinks on Windows")

    constants.LOCAL_BIN_DIR.mkdir(exist_ok=True, parents=True)
    (constants.LOCAL_BIN_DIR / "pycowsay").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


def test_install_python3_5(pipx_temp_env):
    if PYTHON3_5:
        assert not run_pipx_cli(["install", "cowsay", "--python", PYTHON3_5])
    else:
        pytest.skip("python3.5 not on PATH")


def test_pip_args_forwarded_to_package_name_determination(
    pipx_temp_env, caplog, capsys
):
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
