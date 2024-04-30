import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest  # type: ignore

from helpers import app_name, run_pipx_cli, skip_if_windows, unwrap_log_text
from package_info import PKG
from pipx import paths, shared_libs

TEST_DATA_PATH = "./testdata/test_package_specifier"


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--help"])
    captured = capsys.readouterr()
    assert "apps you can run from anywhere" in captured.out


def install_packages(capsys, pipx_temp_env, caplog, packages, package_names=()):
    if len(package_names) != len(packages):
        package_names = packages

    run_pipx_cli(["install", *packages, "--verbose"])
    captured = capsys.readouterr()
    for package_name in package_names:
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
def test_install_easy_packages(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_install_easy_multiple_packages(capsys, pipx_temp_env, caplog):
    install_packages(
        capsys,
        pipx_temp_env,
        caplog,
        ["pycowsay", PKG["black"]["spec"]],
        ["pycowsay", "black"],
    )


@pytest.mark.parametrize(
    "package_name, package_spec",
    [("pycowsay", "pycowsay"), ("black", PKG["black"]["spec"])],
)
@skip_if_windows
def test_install_easy_packages_globally(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("cloudtoken", PKG["cloudtoken"]["spec"]),
        ("awscli", PKG["awscli"]["spec"]),
        ("ansible", PKG["ansible"]["spec"]),
        ("shell-functools", PKG["shell-functools"]["spec"]),
    ],
)
def test_install_tricky_packages(capsys, pipx_temp_env, caplog, package_name, package_spec):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")
    if sys.platform.startswith("win") and package_name == "ansible":
        pytest.skip("Ansible is not installable on Windows")

    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_install_tricky_multiple_packages(capsys, pipx_temp_env, caplog):
    if os.getenv("FAST"):
        pytest.skip("skipping slow tests")

    packages = ["cloudtoken", "awscli", "shell-functools"]
    package_specs = [PKG[package]["spec"] for package in packages]

    install_packages(capsys, pipx_temp_env, caplog, package_specs, packages)


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("pycowsay", "git+https://github.com/cs01/pycowsay.git@master"),
        ("pylint", PKG["pylint"]["spec"]),
        ("nox", "https://github.com/wntrblm/nox/archive/2022.1.7.zip"),
    ],
)
def test_install_package_specs(capsys, pipx_temp_env, caplog, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


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
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "'pycowsay' already seems to be installed. Not modifying existing installation" in captured.out


def test_include_deps(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", PKG["jupyter"]["spec"]]) == 1
    assert not run_pipx_cli(["install", PKG["jupyter"]["spec"], "--include-deps"])


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("zest-releaser", PKG["zest-releaser"]["spec"]),
        ("tox-ini-fmt", PKG["tox-ini-fmt"]["spec"]),
    ],
)
def test_name_tricky_characters(caplog, capsys, pipx_temp_env, package_name, package_spec):
    install_packages(capsys, pipx_temp_env, caplog, [package_spec], [package_name])


def test_extra(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "nox[tox_to_nox]==2023.4.22", "--include-deps"])
    captured = capsys.readouterr()
    assert f"- {app_name('tox')}\n" in captured.out


def test_install_local_extra(pipx_temp_env, capsys, monkeypatch, root):
    assert not run_pipx_cli(["install", str(root / f"{TEST_DATA_PATH}/local_extras[cow]"), "--include-deps"])
    captured = capsys.readouterr()
    assert f"- {app_name('pycowsay')}\n" in captured.out
    assert f"- {Path('man6/pycowsay.6')}\n" in captured.out


def test_path_warning(pipx_temp_env, capsys, monkeypatch, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert "is not on your PATH environment variable" not in unwrap_log_text(caplog.text)

    monkeypatch.setenv("PATH", "")
    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    assert "is not on your PATH environment variable" in unwrap_log_text(caplog.text)


@skip_if_windows
def test_existing_symlink_points_to_existing_wrong_location_warning(pipx_temp_env, caplog, capsys):
    paths.ctx.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.ctx.bin_dir / "pycowsay").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in unwrap_log_text(caplog.text)
    assert "symlink missing or pointing to unexpected location" in captured.out
    # bin dir was on path, so the warning should NOT appear (even though the symlink
    # pointed to the wrong location)
    assert "is not on your PATH environment variable" not in captured.err


@skip_if_windows
def test_existing_man_page_symlink_points_to_existing_wrong_location_warning(pipx_temp_env, caplog, capsys):
    (paths.ctx.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.ctx.man_dir / "man6" / "pycowsay.6").symlink_to(os.devnull)
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "File exists at" in unwrap_log_text(caplog.text)
    assert "symlink missing or pointing to unexpected location" in captured.out


@skip_if_windows
def test_existing_symlink_points_to_nothing(pipx_temp_env, capsys):
    paths.ctx.bin_dir.mkdir(exist_ok=True, parents=True)
    (paths.ctx.bin_dir / "pycowsay").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


@skip_if_windows
def test_existing_man_page_symlink_points_to_nothing(pipx_temp_env, capsys):
    (paths.ctx.man_dir / "man6").mkdir(exist_ok=True, parents=True)
    (paths.ctx.man_dir / "man6" / "pycowsay.6").symlink_to("/asdf/jkl")
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    # pipx should realize the symlink points to nothing and replace it,
    # so no warning should be present
    assert "symlink missing or pointing to unexpected location" not in captured.out


def test_pip_args_forwarded_to_shared_libs(pipx_ultra_temp_env, capsys, caplog):
    # strategy:
    # 1. start from an empty env to ensure the next command would trigger a shared lib update
    assert shared_libs.shared_libs.needs_upgrade
    # 2. install any package with --no-index
    # and check that the shared library update phase fails
    return_code = run_pipx_cli(["install", "--verbose", "--pip-args=--no-index", "pycowsay"])
    assert "Upgrading shared libraries in" in caplog.text

    captured = capsys.readouterr()
    assert return_code != 0
    assert "ERROR: Could not find a version that satisfies the requirement pip" in captured.err
    assert "Failed to upgrade shared libraries" in caplog.text


def test_pip_args_forwarded_to_package_name_determination(pipx_temp_env, capsys):
    assert run_pipx_cli(
        [
            "install",
            # use a valid spec and invalid pip args
            "https://github.com/psf/black/archive/22.8.0.zip",
            "--verbose",
            "--pip-args='--asdf'",
        ]
    )
    captured = capsys.readouterr()
    assert "Cannot determine package name from spec" in captured.err


def test_pip_args_with_windows_path(pipx_temp_env, capsys):
    if not sys.platform.startswith("win"):
        pytest.skip("Test pip arguments with Windows path on Windows only.")

    assert run_pipx_cli(
        [
            "install",
            "pycowsay",
            "--verbose",
            "--pip-args='--no-index --find-links=D:\\TEST\\DIR'",
        ]
    )
    captured = capsys.readouterr()
    assert r"D:\\TEST\\DIR" in captured.err


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

    assert (paths.ctx.bin_dir / name_a).exists()
    assert (paths.ctx.bin_dir / name_b).exists()


def test_man_page_install(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert f"- {Path('man6/pycowsay.6')}" in captured.out
    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").exists()


def test_install_pip_failure(pipx_temp_env, capsys):
    assert run_pipx_cli(["install", "weblate==4.3.1", "--verbose"])
    captured = capsys.readouterr()

    assert "Fatal error from pip" in captured.err

    pip_log_file_match = re.search(r"Full pip output in file:\s+(\S.+)$", captured.err, re.MULTILINE)
    assert pip_log_file_match
    assert Path(pip_log_file_match[1]).exists()

    assert re.search(r"pip (failed|seemed to fail) to build package", captured.err)


def test_install_local_archive(pipx_temp_env, monkeypatch, capsys, root):
    monkeypatch.chdir(root / TEST_DATA_PATH / "local_extras")

    subprocess.run([sys.executable, "-m", "pip", "wheel", "."], check=True)
    assert not run_pipx_cli(["install", "repeatme-0.1-py3-none-any.whl"])
    captured = capsys.readouterr()
    assert f"- {app_name('repeatme')}\n" in captured.out


def test_force_install_changes(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "https://github.com/wntrblm/nox/archive/2022.1.7.zip"])
    captured = capsys.readouterr()
    assert "2022.1.7" in captured.out

    assert not run_pipx_cli(["install", "nox", "--force"])
    captured = capsys.readouterr()
    assert "2022.1.7" not in captured.out


def test_force_install_changes_editable(pipx_temp_env, root, capsys):
    empty_project_path_as_string = (root / "testdata" / "empty_project").as_posix()
    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string])
    captured = capsys.readouterr()
    assert "empty-project" in captured.out

    assert not run_pipx_cli(["install", "--editable", empty_project_path_as_string, "--force"])
    captured = capsys.readouterr()
    assert "Installing to existing venv 'empty-project'" in captured.out


def test_preinstall(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "black", "nox"])
    assert "black" in caplog.text


def test_preinstall_multiple(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "chardet", "--preinstall", "colorama", "nox"])
    assert "chardet" in caplog.text
    assert "colorama" in caplog.text


def test_preinstall_specific_version(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "--preinstall", "black==22.8.0", "nox"])
    assert "black==22.8.0" in caplog.text


@pytest.mark.xfail
def test_do_not_wait_for_input(pipx_temp_env, pipx_session_shared_dir, monkeypatch):
    monkeypatch.setenv("PIP_INDEX_URL", "http://127.0.0.1:8080/simple")
    run_pipx_cli(["install", "pycowsay"])


def test_passed_python_and_force_flag_warning(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["install", "--python", sys.executable, "--force", "black"])
    captured = capsys.readouterr()
    assert "--python is ignored when --force is passed." in captured.out

    assert not run_pipx_cli(["install", "black", "--force"])
    captured = capsys.readouterr()
    assert (
        "--python is ignored when --force is passed." not in captured.out
    ), "Should only print warning if both flags present"

    assert not run_pipx_cli(["install", "pycowsay", "--force"])
    captured = capsys.readouterr()
    assert (
        "--python is ignored when --force is passed." not in captured.out
    ), "Should not print warning if package does not exist yet"


@pytest.mark.parametrize(
    "python_version",
    ["3.0", "3.1"],
)
def test_install_fetch_missing_python_invalid(capsys, python_version):
    assert run_pipx_cli(["install", "--python", python_version, "--fetch-missing-python", "pycowsay"])
    captured = capsys.readouterr()
    assert f"No executable for the provided Python version '{python_version}' found" in captured.out


def test_install_run_in_separate_directory(caplog, capsys, pipx_temp_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    f = Path("argparse.py")
    f.touch()

    install_packages(capsys, pipx_temp_env, caplog, ["pycowsay"], ["pycowsay"])


@skip_if_windows
@pytest.mark.parametrize(
    "python_version",
    [
        str(sys.version_info.major),
        f"{sys.version_info.major}.{sys.version_info.minor}",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ],
)
def test_install_python_command_version(pipx_temp_env, monkeypatch, capsys, python_version):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert python_version in captured.out


@skip_if_windows
def test_install_python_command_version_invalid(pipx_temp_env, capsys):
    python_version = "3.x"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Invalid Python version: {python_version}" in captured.err


@skip_if_windows
def test_install_python_command_version_unsupported(pipx_temp_env, capsys):
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.dev"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Unsupported Python version: {python_version}" in captured.err


@skip_if_windows
def test_install_python_command_version_missing(pipx_temp_env, monkeypatch, capsys):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    python_version = f"{sys.version_info.major + 99}.{sys.version_info.minor}"
    assert run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"Command `python{python_version}` was not found" in captured.err


@skip_if_windows
def test_install_python_command_version_micro_mismatch(pipx_temp_env, monkeypatch, capsys):
    monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro + 1}"
    assert not run_pipx_cli(["install", "--python", python_version, "--verbose", "pycowsay"])
    captured = capsys.readouterr()
    assert f"It may not match the specified version {python_version} at the micro/patch level" in captured.err
