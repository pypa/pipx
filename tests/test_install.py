import os
import sys
from unittest import mock

import pytest  # type: ignore

from helpers import PKGSPEC, run_pipx_cli, which_python
from pipx import constants

PYTHON3_5 = which_python("python3.5")
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
        # https://github.com/pipxproject/pipx/issues/217
        assert "symlink missing or pointing to unexpected location" not in captured.out
    assert "not modifying" not in captured.out
    assert "is not on your PATH environment variable" not in captured.out
    for record in caplog.records:
        assert "⚠️" not in record.message
        assert "WARNING" not in record.message


@pytest.mark.parametrize(
    "package_name, package_spec",
    [("pycowsay", "pycowsay"), ("black", PKGSPEC["black"])],
)
def test_install_easy_packages(
    capsys, pipx_temp_env, caplog, package_name, package_spec
):
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("cloudtoken", PKGSPEC["cloudtoken"]),
        ("awscli", PKGSPEC["awscli"]),
        ("ansible", PKGSPEC["ansible"]),
        ("shell-functools", PKGSPEC["shell-functools"]),
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
        ("pylint", PKGSPEC["pylint"]),
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
    assert run_pipx_cli(["install", PKGSPEC["jupyter"]]) == 1
    assert not run_pipx_cli(["install", PKGSPEC["jupyter"], "--include-deps"])


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("jaraco-financial", "jaraco.financial==2.0.0"),
        ("tox-ini-fmt", PKGSPEC["tox-ini-fmt"]),
    ],
)
def test_name_tricky_characters(
    caplog, capsys, pipx_temp_env, package_name, package_spec
):
    # TODO: remove skip when debug venv_metadata_inspector_legacy.py is removed
    if package_name == "jaraco-financial":
        pytest.skip(
            "Remove this skip when venv_metadata_inspector_legacy.py is removed"
        )

    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


def test_extra(pipx_temp_env, capsys):
    # TODO: remove skip when debug venv_metadata_inspector_legacy.py is removed
    pytest.skip("Remove this skip when venv_metadata_inspector_legacy.py is removed")

    assert not run_pipx_cli(["install", "nox[tox_to_nox]==2020.8.22", "--include-deps"])
    captured = capsys.readouterr()
    assert "- tox\n" in captured.out


def test_install_local_extra(pipx_temp_env, capsys):
    # TODO: remove skip when debug venv_metadata_inspector_legacy.py is removed
    pytest.skip("Remove this skip when venv_metadata_inspector_legacy.py is removed")

    assert not run_pipx_cli(
        ["install", TEST_DATA_PATH + "/local_extras[cow]", "--include-deps"]
    )
    captured = capsys.readouterr()
    assert "- pycowsay\n" in captured.out


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


def test_install_suffix(pipx_temp_env, capsys):
    name = "pbr"

    suffix = "_a"
    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_a = f"{name}{suffix}{'.exe' if constants.WINDOWS else ''}"
    assert f"- {name_a}" in captured.out

    suffix = "_b"
    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    captured = capsys.readouterr()
    name_b = f"{name}{suffix}{'.exe' if constants.WINDOWS else ''}"
    assert f"- {name_b}" in captured.out

    assert (constants.LOCAL_BIN_DIR / name_a).exists()
    assert (constants.LOCAL_BIN_DIR / name_b).exists()


# Packages that need prebuilt wheels before pytest is run
#   lektor==3.2.0
#   weblate==4.3.1
#   gns3-gu==2.2.15
#   grow==1.0.0a10
#   nikola==8.1.1
@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("lektor", PKGSPEC["lektor"]),
        ("retext", PKGSPEC["retext"]),
        ("sphinx", PKGSPEC["sphinx"]),
        ("weblate", PKGSPEC["weblate"]),  # py3.9 FAIL lxml<4.7.0,>=4.0
        ("zeo", PKGSPEC["zeo"]),
        ("ansible", PKGSPEC["ansible"]),
        ("awscli", PKGSPEC["awscli"]),
        ("b2", PKGSPEC["b2"]),
        ("beancount", PKGSPEC["beancount"]),  # py3.9 FAIL lxml
        ("beets", PKGSPEC["beets"]),
        ("black", PKGSPEC["black"]),
        ("cactus", PKGSPEC["cactus"]),
        ("chert", PKGSPEC["chert"]),
        ("cloudtoken", PKGSPEC["cloudtoken"]),
        ("coala", PKGSPEC["coala"]),
        ("cookiecutter", PKGSPEC["cookiecutter"]),
        ("cython", PKGSPEC["cython"]),
        ("datasette", PKGSPEC["datasette"]),
        ("diffoscope", PKGSPEC["diffoscope"]),
        ("doc2dash", PKGSPEC["doc2dash"]),
        ("doitlive", PKGSPEC["doitlive"]),
        ("gdbgui", PKGSPEC["gdbgui"]),
        ("gns3-gui", PKGSPEC["gns3-gui"]),
        ("grow", PKGSPEC["grow"]),
        ("guake", PKGSPEC["guake"]),
        ("gunicorn", PKGSPEC["gunicorn"]),
        ("howdoi", PKGSPEC["howdoi"]),  # py3.9 FAIL lxml
        ("httpie", PKGSPEC["httpie"]),
        ("hyde", PKGSPEC["hyde"]),  # py3.9 FAIL pyyaml
        ("ipython", PKGSPEC["ipython"]),
        ("isort", PKGSPEC["isort"]),
        ("kibitzr", PKGSPEC["kibitzr"]),  # py3.9 FAIL lxml
        ("klaus", PKGSPEC["klaus"]),
        ("kolibri", PKGSPEC["kolibri"]),
        ("localstack", PKGSPEC["localstack"]),
        # ("mackup", PKGSPEC["mackup"]),  # NOTE: ONLY FOR mac, linux
        ("magic-wormhole", PKGSPEC["magic-wormhole"]),
        ("mayan-edms", PKGSPEC["mayan-edms"]),  # py3.9 FAIL pillow
        ("mycli", PKGSPEC["mycli"]),
        ("nikola", PKGSPEC["nikola"]),  # py3.9 FAIL lxml
        ("nox", PKGSPEC["nox"]),
        ("pelican", PKGSPEC["pelican"]),
        ("platformio", PKGSPEC["platformio"]),
        ("ppci", PKGSPEC["ppci"]),
        ("prosopopee", PKGSPEC["prosopopee"]),
        ("ptpython", PKGSPEC["ptpython"]),
        ("pycowsay", PKGSPEC["pycowsay"]),
        ("pylint", PKGSPEC["pylint"]),
        ("robotframework", PKGSPEC["robotframework"]),
        ("shell-functools", PKGSPEC["shell-functools"]),
        ("speedtest-cli", PKGSPEC["speedtest-cli"]),
        ("sqlmap", PKGSPEC["sqlmap"]),
        ("streamlink", PKGSPEC["streamlink"]),
        ("taguette", PKGSPEC["taguette"]),
        ("term2048", PKGSPEC["term2048"]),
        ("tox-ini-fmt", PKGSPEC["tox-ini-fmt"]),
        ("visidata", PKGSPEC["visidata"]),
        ("vulture", PKGSPEC["vulture"]),
        ("youtube-dl", PKGSPEC["youtube-dl"]),
    ],
)
@pytest.mark.all_packages
def test_all_packages(capsys, pipx_temp_env, caplog, package_name, package_spec):
    # as many cross-platform packages as possible installable with pipx
    print(sys.version_info[:2])
    if sys.version_info[:2] == (3, 9) and package_name in (
        # Fail to build under py3.9 (2020-10-29)
        "weblate",
        "beancount",
        "howdoi",
        "hyde",
        "kibitzr",
        "mayan-edms",
        "nikola",
    ):
        pytest.skip("This package currently won't compile under Python3.9")
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)


# FAILED PACKAGES TO INVESTIGATE
# jaraco.financial
#   GOOD old doesn't work, but new venv_metadata_inspector.py works!
# kaggle
#   could just be that slugify is in two separate deps, so debug flags error
# mkdocs
#   GOOD (old metadata missing extras in deps)
@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("jaraco-financial", "jaraco.financial==2.0"),
        ("kaggle", PKGSPEC["kaggle"]),
        ("mkdocs", PKGSPEC["mkdocs"]),
    ],
)
@pytest.mark.all_packages
def test_all_packages_problem(
    capsys, pipx_temp_env, caplog, package_name, package_spec
):
    # as many cross-platform packages as possible installable with pipx
    install_package(capsys, pipx_temp_env, caplog, package_spec, package_name)
