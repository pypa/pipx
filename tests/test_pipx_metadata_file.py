import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest
from pytest_mock import MockerFixture

from helpers import assert_package_metadata, create_package_info_ref, run_pipx_cli
from package_info import PKG
from pipx import paths, pipx_metadata_file
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, JsonEncoderHandlesPath, PackageInfo, PipxMetadata
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
    man_pages=[str(Path("man1/testapp.1"))],
    man_pages_of_dependencies=[str(Path("man1/dep1.1"))],
    man_paths_of_dependencies={"dep1": [Path("man1/dep1.1")]},
    package_version="0.1.2",
    expected_apps=["testapp"],
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
    man_pages=[str(Path("man1/injapp.1"))],
    man_pages_of_dependencies=[str(Path("man1/dep2.1"))],
    man_paths_of_dependencies={"dep2": [Path("man1/dep2.1")]},
    package_version="6.7.8",
)


def test_json_encoder_rejects_unsupported_value() -> None:
    with pytest.raises(TypeError, match=r"complex.*not JSON serializable"):
        json.dumps(1j, cls=JsonEncoderHandlesPath)


def test_pipx_metadata_file_create(tmp_path: Path) -> None:
    assert TEST_PACKAGE1.package is not None
    venv_dir = tmp_path / TEST_PACKAGE1.package
    venv_dir.mkdir()

    pipx_metadata = PipxMetadata(venv_dir)
    pipx_metadata.main_package = TEST_PACKAGE1
    pipx_metadata.environment = "test-package"
    pipx_metadata.python_version = "3.4.5"
    pipx_metadata.source_interpreter = Path(sys.executable)
    pipx_metadata.venv_args = ["--system-site-packages"]
    pipx_metadata.injected_packages = {"injected": TEST_PACKAGE2}
    pipx_metadata.exposure_enabled = False
    pipx_metadata.write()

    pipx_metadata2 = PipxMetadata(venv_dir)

    for attribute in [
        "venv_dir",
        "environment",
        "main_package",
        "python_version",
        "venv_args",
        "injected_packages",
        "exposure_enabled",
    ]:
        assert getattr(pipx_metadata, attribute) == getattr(pipx_metadata2, attribute)


def test_pipx_metadata_file_defaults_exposure_for_version_0_6(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    metadata = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    payload = metadata.to_dict()
    payload["pipx_metadata_version"] = "0.6"
    payload.pop("exposure_enabled")
    (venv_dir / PIPX_INFO_FILENAME).write_text(
        json.dumps(payload, cls=JsonEncoderHandlesPath),
        encoding="utf-8",
    )

    assert PipxMetadata(venv_dir).exposure_enabled is True


def test_pipx_metadata_file_defaults_expected_apps_from_version_0_7(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    metadata = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    payload = metadata.to_dict()
    payload["pipx_metadata_version"] = "0.7"
    payload["main_package"].pop("expected_apps")
    (venv_dir / PIPX_INFO_FILENAME).write_text(json.dumps(payload, cls=JsonEncoderHandlesPath))

    assert PipxMetadata(venv_dir).main_package.expected_apps == []


def test_pipx_metadata_file_defaults_lock_file_from_version_0_8(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    metadata = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    payload = metadata.to_dict()
    payload["pipx_metadata_version"] = "0.8"
    payload["main_package"].pop("lock_file")
    (venv_dir / PIPX_INFO_FILENAME).write_text(json.dumps(payload, cls=JsonEncoderHandlesPath))

    assert PipxMetadata(venv_dir).main_package.lock_file is None


def test_pipx_metadata_file_defaults_environment_from_version_0_8(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    metadata = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    payload = metadata.to_dict()
    payload["pipx_metadata_version"] = "0.8"
    payload.pop("environment")
    (venv_dir / PIPX_INFO_FILENAME).write_text(json.dumps(payload, cls=JsonEncoderHandlesPath))

    assert PipxMetadata(venv_dir).environment is None


def test_pipx_metadata_file_defaults_included_apps_from_version_0_9(tmp_path: Path) -> None:
    venv_dir: Final[Path] = tmp_path / "venv"
    venv_dir.mkdir()
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    (venv_dir / PIPX_INFO_FILENAME).write_text(
        json.dumps(metadata.to_dict(), cls=JsonEncoderHandlesPath)
        .replace('"pipx_metadata_version": "0.11"', '"pipx_metadata_version": "0.9"')
        .replace('"include_apps_from": [], ', "")
    )

    assert PipxMetadata(venv_dir).main_package.include_apps_from == []


def test_pipx_metadata_file_defaults_cooldown_from_version_0_10(tmp_path: Path) -> None:
    venv_dir: Final[Path] = tmp_path / "venv"
    venv_dir.mkdir()
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    (venv_dir / PIPX_INFO_FILENAME).write_text(
        json.dumps(metadata.to_dict(), cls=JsonEncoderHandlesPath)
        .replace('"pipx_metadata_version": "0.11"', '"pipx_metadata_version": "0.10"')
        .replace('"cooldown_days": null, ', "")
    )

    assert PipxMetadata(venv_dir).main_package.cooldown_days is None


@pytest.mark.parametrize(
    "test_package",
    [
        replace(TEST_PACKAGE1, include_apps=False),
        replace(TEST_PACKAGE1, package=None),
        replace(TEST_PACKAGE1, package_or_url=None),
    ],
)
def test_pipx_metadata_file_validation(tmp_path, test_package):
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    pipx_metadata = PipxMetadata(venv_dir)
    pipx_metadata.main_package = test_package
    pipx_metadata.python_version = "3.4.5"
    pipx_metadata.source_interpreter = Path(sys.executable)
    pipx_metadata.venv_args = ["--system-site-packages"]
    pipx_metadata.injected_packages = {}

    with pytest.raises(PipxError):
        pipx_metadata.write()


def test_write_preserves_existing_metadata_after_os_error(
    tmp_path: Path,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    metadata_path = venv_dir / PIPX_INFO_FILENAME
    previous_metadata = '{"existing": true}'
    metadata_path.write_text(previous_metadata, encoding="utf-8")
    metadata = PipxMetadata(venv_dir, read=False)
    metadata.main_package = TEST_PACKAGE1
    mocker.patch.object(pipx_metadata_file.json, "dump", side_effect=OSError("disk full"))

    metadata.write()

    assert (
        metadata_path.read_text(encoding="utf-8"),
        sorted(path.name for path in venv_dir.iterdir()),
        f"Unable to write {PIPX_INFO_FILENAME}" in caplog.text,
    ) == (previous_metadata, [PIPX_INFO_FILENAME], True)


def test_package_install(monkeypatch, tmp_path, pipx_temp_env):
    pipx_venvs_dir = paths.ctx.home / "venvs"

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()

    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")
    pycowsay_package_ref = create_package_info_ref("pycowsay", "pycowsay", pipx_venvs_dir)
    assert_package_metadata(pipx_metadata.main_package, pycowsay_package_ref)
    assert pipx_metadata.injected_packages == {}


def test_package_inject(monkeypatch, tmp_path, pipx_temp_env):
    pipx_venvs_dir = paths.ctx.home / "venvs"

    run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])

    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()
    pipx_metadata = PipxMetadata(pipx_venvs_dir / "pycowsay")

    assert pipx_metadata.injected_packages.keys() == {"black"}
    black_package_ref = create_package_info_ref("pycowsay", "black", pipx_venvs_dir, include_apps=False)
    assert_package_metadata(pipx_metadata.injected_packages["black"], black_package_ref)
