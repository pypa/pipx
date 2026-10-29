from __future__ import annotations

import json
import operator
import os
import stat
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest

from helpers import (
    LEGACY_MAIN_PACKAGE,
    SKIP_IF_WINDOWS,
    LegacyMetadata,
    assert_package_metadata,
    create_package_info_ref,
    run_pipx_cli,
)
from package_info import PKG
from pipx import paths, pipx_metadata_file
from pipx.backends import UV
from pipx.constants import PIPX_SHARED_PTH
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, JsonEncoderHandlesPath, PackageInfo, PipxMetadata
from pipx.util import PipxError, redact_url_credentials
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

_MAIN_PACKAGE: Final[PackageInfo] = PackageInfo(
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
_INJECTED_PACKAGE: Final[PackageInfo] = PackageInfo(
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


@pytest.fixture
def venv_dir(tmp_path: Path) -> Path:
    (venv := tmp_path / "venv").mkdir()
    return venv


@pytest.fixture
def payload(venv_dir: Path) -> dict[str, Any]:
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir, read=False)
    metadata.main_package = _MAIN_PACKAGE
    return metadata.to_dict()


@pytest.fixture
def read_payload(venv_dir: Path) -> Callable[[dict[str, Any]], PipxMetadata]:
    def read(payload: dict[str, Any]) -> PipxMetadata:
        (venv_dir / PIPX_INFO_FILENAME).write_text(json.dumps(payload, cls=JsonEncoderHandlesPath), encoding="utf-8")
        return PipxMetadata(venv_dir)

    return read


def test_json_encoder_rejects_unsupported_value() -> None:
    with pytest.raises(TypeError, match=r"complex.*not JSON serializable"):
        json.dumps(1j, cls=JsonEncoderHandlesPath)


def test_pipx_metadata_file_create(venv_dir: Path) -> None:
    pipx_metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    pipx_metadata.main_package = _MAIN_PACKAGE
    pipx_metadata.environment = "test-package"
    pipx_metadata.python_version = "3.4.5"
    pipx_metadata.source_interpreter = Path(sys.executable)
    pipx_metadata.venv_args = ["--system-site-packages"]
    pipx_metadata.injected_packages = {"inj_package": _INJECTED_PACKAGE}
    pipx_metadata.exposure_enabled = False
    pipx_metadata.write()
    recorded: Final = operator.attrgetter(
        "venv_dir",
        "environment",
        "main_package",
        "python_version",
        "venv_args",
        "injected_packages",
        "exposure_enabled",
    )

    assert recorded(PipxMetadata(venv_dir)) == recorded(pipx_metadata)


def test_pipx_metadata_file_defaults_exposure_for_version_0_6(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.6"
    payload.pop("exposure_enabled")

    assert read_payload(payload).exposure_enabled is True


def test_pipx_metadata_file_defaults_expected_apps_from_version_0_7(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.7"
    payload["main_package"].pop("expected_apps")

    assert read_payload(payload).main_package.expected_apps == []


def test_pipx_metadata_file_defaults_lock_file_from_version_0_8(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.8"
    payload["main_package"].pop("lock_file")

    assert read_payload(payload).main_package.lock_file is None


def test_pipx_metadata_file_defaults_environment_from_version_0_8(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.8"
    payload.pop("environment")

    assert read_payload(payload).environment is None


def test_pipx_metadata_file_defaults_included_apps_from_version_0_9(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.9"
    payload["main_package"].pop("include_resources_from")

    assert read_payload(payload).main_package.include_resources_from == []


def test_pipx_metadata_file_migrates_include_apps_from(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["main_package"].pop("include_resources_from")
    payload["main_package"]["include_apps_from"] = ["numpy"]

    assert read_payload(payload).main_package.include_resources_from == ["numpy"]


def test_pipx_metadata_file_keys_injected_package_by_name(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["main_package"]["suffix"] = "@1"
    payload["injected_packages"] = {"inj_package@1": asdict(replace(_INJECTED_PACKAGE, suffix="@1"))}

    assert list(read_payload(payload).injected_packages) == ["inj_package"]


def test_pipx_metadata_file_defaults_cooldown_from_version_0_10(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["pipx_metadata_version"] = "0.10"
    payload["main_package"].pop("cooldown_days")

    assert read_payload(payload).main_package.cooldown_days is None


def test_pipx_metadata_file_keeps_only_recordable_venv_args(
    tmp_path: Path, payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata]
) -> None:
    payload["venv_args"] = ["--clear", str(tmp_path / "other"), "--system-site-packages"]

    assert read_payload(payload).venv_args == ["--system-site-packages"]


def test_pipx_metadata_file_warns_about_ignored_venv_args(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata], caplog: pytest.LogCaptureFixture
) -> None:
    payload["venv_args"] = ["--clear", "other"]

    read_payload(payload)

    assert "venv: ignoring recorded venv arguments --clear other" in caplog.text


def test_pipx_metadata_file_reads_unknown_backend_as_pip(
    payload: dict[str, Any], read_payload: Callable[[dict[str, Any]], PipxMetadata], caplog: pytest.LogCaptureFixture
) -> None:
    payload["backend"] = "conda"

    assert (
        read_payload(payload).backend,
        "venv: ignoring unknown recorded backend 'conda'; treating as 'pip'." in caplog.text,
    ) == ("pip", True)


def test_metadata_round_trip_includes_backend(tmp_path: Path) -> None:
    (venv_dir := tmp_path / "venv").mkdir()
    metadata: Final = pipx_metadata_file.PipxMetadata(venv_dir, read=False)
    metadata.main_package = pipx_metadata_file.PackageInfo(
        package="demo",
        package_or_url="demo",
        pip_args=[],
        include_dependencies=False,
        include_apps=True,
        apps=["demo"],
        app_paths=[Path("demo")],
        apps_of_dependencies=[],
        app_paths_of_dependencies={},
        package_version="1.0",
    )
    metadata.python_version = "3.12"
    metadata.backend = "uv"

    metadata.write()

    assert (
        json.loads((venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).read_text())["backend"],
        pipx_metadata_file.PipxMetadata(venv_dir).backend,
    ) == ("uv", "uv")


def test_metadata_version_order_for_shared_libs(tmp_path: Path) -> None:
    venv_dir: Final[Path] = tmp_path / "venv"
    (site_packages := venv_dir / "lib/python/site-packages").mkdir(parents=True)
    (site_packages / PIPX_SHARED_PTH).touch()
    venv: Final = Venv(venv_dir)
    venv.pipx_metadata.read_metadata_version = "0.10"
    venv.pipx_metadata.backend = UV

    assert venv.uses_shared_libs is False


def test_legacy_metadata_defaults_to_pip(tmp_path: Path) -> None:
    (venv_dir := tmp_path / "venv").mkdir()
    legacy_payload: Final[LegacyMetadata] = {
        "main_package": LEGACY_MAIN_PACKAGE,
        "python_version": "3.12",
        "source_interpreter": None,
        "venv_args": [],
        "injected_packages": {},
        "pipx_metadata_version": "0.5",
    }
    (venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).write_text(json.dumps(legacy_payload))

    assert pipx_metadata_file.PipxMetadata(venv_dir).backend == "pip"


@pytest.mark.parametrize(
    "test_package",
    [
        pytest.param(replace(_MAIN_PACKAGE, include_apps=False), id="without-apps"),
        pytest.param(replace(_MAIN_PACKAGE, package=None), id="without-package"),
        pytest.param(replace(_MAIN_PACKAGE, package_or_url=None), id="without-package-or-url"),
    ],
)
def test_pipx_metadata_file_validation(venv_dir: Path, test_package: PackageInfo) -> None:
    pipx_metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    pipx_metadata.main_package = test_package

    with pytest.raises(PipxError, match="PipxMetadata is corrupt"):
        pipx_metadata.write()


def test_write_preserves_existing_metadata_after_os_error(
    venv_dir: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    metadata_path: Final[Path] = venv_dir / PIPX_INFO_FILENAME
    previous_metadata: Final[str] = '{"existing": true}'
    metadata_path.write_text(previous_metadata, encoding="utf-8")
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir, read=False)
    metadata.main_package = _MAIN_PACKAGE
    mocker.patch.object(Path, "replace", side_effect=OSError("disk full"))

    metadata.write()

    assert (
        metadata_path.read_text(encoding="utf-8"),
        sorted(path.name for path in venv_dir.iterdir()),
        f"Unable to write {PIPX_INFO_FILENAME}" in caplog.text,
    ) == (previous_metadata, [PIPX_INFO_FILENAME], True)


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda path: path.write_bytes(b'{"a": 1}'), id="replaced"),
        pytest.param(Path.unlink, id="removed"),
    ],
)
def test_preserved_restores_the_record(tmp_path: Path, change: Callable[[Path], int | None]) -> None:
    (metadata_path := tmp_path / PIPX_INFO_FILENAME).write_bytes(b"{}")

    with PipxMetadata(tmp_path, read=False).preserved():
        change(metadata_path)

    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == {PIPX_INFO_FILENAME: b"{}"}


def test_preserved_removes_a_record_the_block_created(tmp_path: Path) -> None:
    with PipxMetadata(tmp_path, read=False).preserved():
        (tmp_path / PIPX_INFO_FILENAME).write_bytes(b"{}")

    assert list(tmp_path.iterdir()) == []


@SKIP_IF_WINDOWS
def test_write_keeps_metadata_owner_only(venv_dir: Path) -> None:
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir, read=False)
    metadata.main_package = _MAIN_PACKAGE
    previous_umask: Final[int] = os.umask(0o022)
    try:
        metadata.write()
    finally:
        os.umask(previous_umask)

    # pip_args and package_or_url keep index credentials as given
    assert stat.S_IMODE((venv_dir / PIPX_INFO_FILENAME).stat().st_mode) == 0o600


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_install() -> None:
    pipx_venvs_dir: Final[Path] = paths.CTX.home / "venvs"

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()

    pipx_metadata: Final[PipxMetadata] = PipxMetadata(pipx_venvs_dir / "pycowsay")
    assert_package_metadata(pipx_metadata.main_package, create_package_info_ref("pycowsay", "pycowsay", pipx_venvs_dir))
    assert pipx_metadata.injected_packages == {}


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_inject() -> None:
    pipx_venvs_dir: Final[Path] = paths.CTX.home / "venvs"

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])

    assert (pipx_venvs_dir / "pycowsay" / "pipx_metadata.json").is_file()
    pipx_metadata: Final[PipxMetadata] = PipxMetadata(pipx_venvs_dir / "pycowsay")

    assert pipx_metadata.injected_packages.keys() == {"black"}
    black_package_ref: Final[PackageInfo] = create_package_info_ref(
        "pycowsay", "black", pipx_venvs_dir, include_apps=False
    )
    assert_package_metadata(pipx_metadata.injected_packages["black"], black_package_ref)


def test_pipx_metadata_corrupt_write_logs_without_url_credentials(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    index: Final[str] = "--index-url=https://u:s3cr3ttok@host/simple"
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir=tmp_path)
    metadata.main_package = replace(_MAIN_PACKAGE, package=None, pip_args=[index])

    with caplog.at_level("DEBUG"), pytest.raises(PipxError, match="PipxMetadata is corrupt"):
        metadata.write()

    assert (redact_url_credentials(index) in caplog.text, "s3cr3ttok" in caplog.text) == (True, False)
