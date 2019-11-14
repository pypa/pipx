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

# Reference metadata for various packages
PYCOWSAY_PACKAGE_REF = PackageInfo(
    package="pycowsay",
    package_or_url="pycowsay",
    pip_args=[],
    include_dependencies=False,
    include_apps=True,
    apps=["pycowsay"],
    app_paths=[Path("pycowsay/bin/pycowsay")],  # Placeholder, not real path
    apps_of_dependencies=[],
    app_paths_of_dependencies={},
    package_version="0.0.0.1",
)
BLACK_PACKAGE_REF = PackageInfo(
    package="black",
    package_or_url="black",
    pip_args=[],
    include_dependencies=False,
    include_apps=True,
    apps=["pycowsay"],
    app_paths=[Path("black/bin/black")],  # Placeholder, not real path
    apps_of_dependencies=[],
    app_paths_of_dependencies={},
    package_version="19.10b3",
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


def assert_package_metadata(test_metadata, ref_metadata):
    # update package version of ref with recent package version
    # only compare sets for apps, app_paths so order is not important

    assert test_metadata.package_version != ""
    assert isinstance(test_metadata.apps, list)
    assert isinstance(test_metadata.app_paths, list)

    test_metadata_replaced = test_metadata._replace(
        apps=set(test_metadata.apps), app_paths=set(test_metadata.apps)
    )
    ref_metadata_replaced = ref_metadata._replace(
        apps=set(ref_metadata.apps),
        app_paths=set(ref_metadata.apps),
        package_version=test_metadata.package_version,
    )
    assert test_metadata_replaced == ref_metadata_replaced


def test_package_install(monkeypatch, tmp_path, pipx_temp_env):
    pipx_venvs_dir = pipx.constants.PIPX_HOME / "venvs"

    # test metadata after package install
    run_pipx_cli(["install", "pycowsay"])
    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")

    if pipx.constants.WINDOWS:
        ref_replacement_fields = {
            "app_paths": [pipx_venvs_dir / "pycowsay" / "Scripts" / "pycowsay.exe"],
            "apps": ["pycowsay", "pycowsay.exe"],
        }
    else:
        ref_replacement_fields = {
            "app_paths": [pipx_venvs_dir / "pycowsay" / "bin" / "pycowsay"]
        }
    assert_package_metadata(
        pipx_metadata.main_package,
        PYCOWSAY_PACKAGE_REF._replace(include_apps=True, **ref_replacement_fields),
    )

    del pipx_metadata

    # test metadata after package inject
    run_pipx_cli(["inject", "pycowsay", "black"])

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")

    if pipx.constants.WINDOWS:
        ref_replacement_fields = {
            "apps": ["black", "black.exe", "blackd", "blackd.exe"],
            "app_paths": [
                pipx_venvs_dir / "pycowsay" / "Scripts" / "black.exe",
                pipx_venvs_dir / "pycowsay" / "Scripts" / "blackd.exe",
            ],
        }
    else:
        ref_replacement_fields = {
            "apps": ["black", "blackd"],
            "app_paths": [
                pipx_venvs_dir / "pycowsay" / "bin" / "black",
                pipx_venvs_dir / "pycowsay" / "bin" / "blackd",
            ],
        }
    assert_package_metadata(
        pipx_metadata.injected_packages["black"],
        BLACK_PACKAGE_REF._replace(include_apps=False, **ref_replacement_fields),
    )
