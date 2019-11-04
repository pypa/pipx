from pathlib import Path
import pytest  # type: ignore

from helpers import assert_not_in_virtualenv, run_pipx_cli
import pipx.constants
from pipx.pipx_metadata_file import PipxMetadata, PackageInfo
from pipx.util import PipxError

assert_not_in_virtualenv()


TEST_PACKAGE1 = PackageInfo(
    package="test_package",
    package_or_url="test_package_url",
    pip_args=[],
    include_apps=True,
    include_dependencies=False,
    apps=["testapp"],
    app_paths=[Path("/usr/bin")],
    apps_of_dependencies=["dep1"],
    app_paths_of_dependencies={"dep1": [Path("bin")]},
    package_version="0.1.2",
)
TEST_PACKAGE2 = PackageInfo(
    package="inj_package",
    package_or_url="inj_package_url",
    pip_args=["-e"],
    include_apps=True,
    include_dependencies=False,
    apps=["injapp"],
    app_paths=[Path("/usr/bin")],
    apps_of_dependencies=["dep2"],
    app_paths_of_dependencies={"dep2": [Path("bin")]},
    package_version="6.7.8",
)


def test_pipx_metadata_file_create(tmp_path):
    pipx_metadata = PipxMetadata(tmp_path)
    pipx_metadata.main_package = TEST_PACKAGE1
    pipx_metadata.python_version = "3.4.5"
    pipx_metadata.venv_args = ["--system-site-packages"]
    pipx_metadata.injected_packages = {"injected": TEST_PACKAGE2}

    pipx_metadata.write()
    del pipx_metadata

    pipx_metadata2 = PipxMetadata(tmp_path)
    assert pipx_metadata2.main_package == TEST_PACKAGE1
    assert pipx_metadata2.python_version == "3.4.5"
    assert pipx_metadata2.venv_args == ["--system-site-packages"]
    assert pipx_metadata2.injected_packages == {"injected": TEST_PACKAGE2}


def test_pipx_metadata_file_validation(tmp_path):
    venv_dir1 = tmp_path / "venv1"
    venv_dir1.mkdir()
    venv_dir2 = tmp_path / "venv2"
    venv_dir2.mkdir()

    test_package1 = TEST_PACKAGE1._replace(include_apps=False)
    test_package2 = TEST_PACKAGE1._replace(package=None)
    test_package3 = TEST_PACKAGE1._replace(package_or_url=None)

    for test_package in [test_package1, test_package2, test_package3]:
        pipx_metadata = PipxMetadata(venv_dir1)
        pipx_metadata.main_package = test_package
        pipx_metadata.python_version = "3.4.5"
        pipx_metadata.venv_args = ["--system-site-packages"]
        pipx_metadata.injected_packages = {}

        with pytest.raises(PipxError):
            pipx_metadata.write()


def test_package_install(monkeypatch, tmp_path, pipx_temp_env):
    pipx_venvs_dir = pipx.constants.PIPX_HOME / "venvs"

    run_pipx_cli(["install", "pycowsay"])
    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    assert pipx_metadata.main_package.package == "pycowsay"
    assert pipx_metadata.main_package.package_or_url == "pycowsay"
    assert pipx_metadata.main_package.pip_args == []
    assert pipx_metadata.main_package.include_dependencies == False
    assert pipx_metadata.main_package.include_apps == True
    assert pipx_metadata.main_package.apps == ["pycowsay"]
    assert pipx_metadata.main_package.app_paths == [
        pipx_venvs_dir / "pycowsay" / "bin" / "pycowsay"
    ]
    assert pipx_metadata.main_package.apps_of_dependencies == []
    assert pipx_metadata.main_package.app_paths_of_dependencies == {}
    assert pipx_metadata.main_package.package_version != ""

    del pipx_metadata

    # TODO 20191103: need simpler non-gcc-compiling package besides black!
    run_pipx_cli(["inject", "pycowsay", "black"])

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    assert pipx_metadata.injected_packages["black"].package == "black"
    assert pipx_metadata.injected_packages["black"].package_or_url == "black"
    assert pipx_metadata.injected_packages["black"].pip_args == []
    assert pipx_metadata.injected_packages["black"].include_dependencies == False
    assert pipx_metadata.injected_packages["black"].include_apps == False
    assert pipx_metadata.injected_packages["black"].apps == ["black", "blackd"]
    assert pipx_metadata.injected_packages["black"].app_paths == [
        pipx_venvs_dir / "pycowsay" / "bin" / "black",
        pipx_venvs_dir / "pycowsay" / "bin" / "blackd",
    ]
    assert pipx_metadata.injected_packages["black"].apps_of_dependencies == []
    assert pipx_metadata.injected_packages["black"].app_paths_of_dependencies == {}
    assert pipx_metadata.injected_packages["black"].package_version != ""
