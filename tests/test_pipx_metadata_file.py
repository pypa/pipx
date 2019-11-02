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


def test_package_install(monkeypatch, tmp_path):
    pipx_home = tmp_path / ".local" / "pipx"
    pipx_home.mkdir(parents=True)
    local_bin_dir = tmp_path / ".local" / "bin"
    local_bin_dir.mkdir(parents=True)
    pipx_local_venvs = pipx_home / "venvs"
    pipx_local_venvs.mkdir(parents=True)
    pipx_shared_libs = pipx_home / "shared"
    pipx_shared_libs.mkdir(parents=True)
    monkeypatch.setattr(pipx.constants, "PIPX_HOME", pipx_home)
    monkeypatch.setattr(pipx.constants, "PIPX_LOCAL_VENVS", pipx_local_venvs)
    monkeypatch.setattr(pipx.constants, "PIPX_SHARED_LIBS", pipx_shared_libs)
    monkeypatch.setattr(pipx.constants, "LOCAL_BIN_DIR", local_bin_dir)

    run_pipx_cli(["install", "pycowsay"])
    assert (pipx_home / "venvs" / "pycowsay" / "pipx_metadata.json").is_file()


# confirm that package install creates pipx_metadata.json
# confirm that package inject adds injected package to pipx metadata
