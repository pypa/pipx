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

    pipx_metadata2 = PipxMetadata(tmp_path)

    for attribute in [
        "venv_dir",
        "main_package",
        "python_version",
        "venv_args",
        "injected_packages",
    ]:
        assert getattr(pipx_metadata, attribute) == getattr(pipx_metadata2, attribute)


@pytest.mark.parametrize(
    "test_package",
    [
        TEST_PACKAGE1._replace(include_apps=False),
        TEST_PACKAGE1._replace(package=None),
        TEST_PACKAGE1._replace(package_or_url=None),
    ],
)
def test_pipx_metadata_file_validation(tmp_path, test_package):
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    pipx_metadata = PipxMetadata(venv_dir)
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
    assert pipx_metadata.main_package.include_dependencies is False
    assert pipx_metadata.main_package.include_apps is True
    if pipx.constants.WINDOWS:
        assert pipx_metadata.main_package.apps == ["pycowsay", "pycowsay.exe"]
        assert pipx_metadata.main_package.app_paths == [
            pipx_venvs_dir / "pycowsay" / "Scripts" / "pycowsay.exe"
        ]
    else:
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
    assert pipx_metadata.injected_packages["black"].include_dependencies is False
    assert pipx_metadata.injected_packages["black"].include_apps is False
    if pipx.constants.WINDOWS:
        # order is not important, so we compare sets
        assert isinstance(pipx_metadata.injected_packages["black"].apps, list)
        # TODO: Issue #217 - Windows should not have non-exe black, blackd
        assert set(pipx_metadata.injected_packages["black"].apps) == {
            "black",
            "black.exe",
            "blackd",
            "blackd.exe",
        }
        assert isinstance(pipx_metadata.injected_packages["black"].app_paths, list)
        assert set(pipx_metadata.injected_packages["black"].app_paths) == {
            pipx_venvs_dir / "pycowsay" / "Scripts" / "black.exe",
            pipx_venvs_dir / "pycowsay" / "Scripts" / "blackd.exe",
        }
    else:
        # order is not important, so we compare sets
        assert isinstance(pipx_metadata.injected_packages["black"].apps, list)
        assert set(pipx_metadata.injected_packages["black"].apps) == {"black", "blackd"}
        assert isinstance(pipx_metadata.injected_packages["black"].app_paths, list)
        assert set(pipx_metadata.injected_packages["black"].app_paths) == {
            pipx_venvs_dir / "pycowsay" / "bin" / "black",
            pipx_venvs_dir / "pycowsay" / "bin" / "blackd",
        }
    assert pipx_metadata.injected_packages["black"].apps_of_dependencies == []
    assert pipx_metadata.injected_packages["black"].app_paths_of_dependencies == {}
    assert pipx_metadata.injected_packages["black"].package_version != ""
