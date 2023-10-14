from pathlib import Path

import pytest  # type: ignore

from helpers import assert_package_metadata, create_package_info_ref, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata
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


def test_pipx_metadata_file_create(tmp_path):
    venv_dir = tmp_path / TEST_PACKAGE1.package
    venv_dir.mkdir()

    pipx_metadata = PipxMetadata(venv_dir)
    pipx_metadata.main_package = TEST_PACKAGE1
    pipx_metadata.python_version = "3.4.5"
    pipx_metadata.venv_args = ["--system-site-packages"]
    pipx_metadata.injected_packages = {"injected": TEST_PACKAGE2}
    pipx_metadata.write()

    pipx_metadata2 = PipxMetadata(venv_dir)

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
    pipx_venvs_dir = paths.ctx.home / "venvs"

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    pycowsay_package_ref = create_package_info_ref(
        "pycowsay", "pycowsay", pipx_venvs_dir
    )
    assert_package_metadata(pipx_metadata.main_package, pycowsay_package_ref)
    assert pipx_metadata.injected_packages == {}


def test_package_inject(monkeypatch, tmp_path, pipx_temp_env):
    pipx_venvs_dir = paths.ctx.home / "venvs"

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])

    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()
    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")

    assert pipx_metadata.injected_packages.keys() == {"black"}
    black_package_ref = create_package_info_ref(
        "pycowsay", "black", pipx_venvs_dir, include_apps=False
    )
    assert_package_metadata(pipx_metadata.injected_packages["black"], black_package_ref)
