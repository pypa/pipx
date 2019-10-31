from pathlib import Path
import pytest  # type: ignore

from pipx.pipx_metadata_file import PipxMetadata, PackageInfo
from pipx.util import PipxError


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


# test to make sure we never have duplicate injected packages
#   this might happen during reinstall_all if we don't properly uninstall
#       injected packages or don't remove their metadata


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
