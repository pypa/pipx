from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import sysconfig
import zipfile
from dataclasses import replace
from typing import TYPE_CHECKING, Final, Protocol, TypedDict
from unittest import mock

import pytest
from packaging.utils import canonicalize_name

from package_info import PKG
from pipx import paths
from pipx.main import cli
from pipx.pipx_metadata_file import JsonEncoderHandlesPath, PackageInfo, PipxMetadata
from pipx.util import get_venv_paths
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

WIN: Final[bool] = sys.platform.startswith("win")

# mirrors scripts/test_packages_support.py: free-threaded builds seed a cache of cp3XXt wheels apart from the
# same-version GIL build's directory
PACKAGE_CACHE_DIR_NAME: Final[str] = (
    f"{sys.version_info[0]}.{sys.version_info[1]}{'t' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''}"
)

# None stands for a venv from before pipx 0.15.0.0, which wrote no metadata file
PIPX_METADATA_LEGACY_VERSIONS: Final[list[str | None]] = [None, "0.1", "0.2", "0.3"]


class MakePylock(Protocol):
    def __call__(self, package: str, version: str, group: str | None = None) -> Path: ...


class LegacyPackageInfo(TypedDict):
    package: str
    package_or_url: str
    pip_args: list[str]
    include_dependencies: bool
    include_apps: bool
    apps: list[str]
    app_paths: list[str]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[str]]
    man_pages: list[str]
    man_paths: list[str]
    man_pages_of_dependencies: list[str]
    man_paths_of_dependencies: dict[str, list[str]]
    package_version: str
    suffix: str
    pinned: bool


class LegacyMetadata(TypedDict):
    main_package: LegacyPackageInfo
    python_version: str
    source_interpreter: None
    venv_args: list[str]
    injected_packages: dict[str, LegacyPackageInfo]
    pipx_metadata_version: str


class CurrentMetadata(LegacyMetadata):
    backend: str


LEGACY_MAIN_PACKAGE: Final[LegacyPackageInfo] = {
    "package": "demo",
    "package_or_url": "demo",
    "pip_args": [],
    "include_dependencies": False,
    "include_apps": True,
    "apps": ["demo"],
    "app_paths": [],
    "apps_of_dependencies": [],
    "app_paths_of_dependencies": {},
    "man_pages": [],
    "man_paths": [],
    "man_pages_of_dependencies": [],
    "man_paths_of_dependencies": {},
    "package_version": "1.0",
    "suffix": "",
    "pinned": False,
}


def app_name(app: str) -> str:
    return f"{app}.exe" if WIN else app


def run_pipx_cli(pipx_args: list[str]) -> int:
    with mock.patch.object(sys, "argv", ["pipx", *pipx_args]):
        return cli()


def pipx_subprocess_env() -> dict[str, str]:
    return os.environ | {
        "PIPX_BIN_DIR": str(paths.CTX.bin_dir),
        "PIPX_HOME": str(paths.CTX.home),
        "PIPX_MAN_DIR": str(paths.CTX.man_dir),
        "PIPX_SHARED_LIBS": str(paths.CTX.shared_libs),
    }


def unwrap_log_text(log_text: str) -> str:
    # a captured log line starts with its severity, so a line opening with spaces continues a wrapped pipx message
    return re.sub(r"\n\s+", " ", log_text)


def current_log_file() -> Path:
    log_file: Final = paths.CTX.log_file
    assert log_file is not None
    return log_file


def mock_legacy_venv(venv_name: str, metadata_version: str | None = None) -> None:
    venv_dir: Final[Path] = paths.CTX.venvs / canonicalize_name(venv_name)
    if metadata_version is None:
        (venv_dir / "pipx_metadata.json").unlink()
        return

    package_keys: Final[list[str]] = [
        "package",
        "package_or_url",
        "pip_args",
        "include_dependencies",
        "include_apps",
        "apps",
        "app_paths",
        "apps_of_dependencies",
        "app_paths_of_dependencies",
        "package_version",
        *(["suffix"] if metadata_version != "0.1" else []),
    ]
    metadata_keys: Final[list[str]] = [
        "main_package",
        "python_version",
        "venv_args",
        *(
            ["man_pages", "man_paths", "man_pages_of_dependencies", "man_paths_of_dependencies"]
            if metadata_version == "0.3"
            else []
        ),
    ]
    modern_metadata: Final = PipxMetadata(venv_dir).to_dict()
    legacy_metadata: Final = {
        **{key: modern_metadata.get(key) for key in metadata_keys},
        "injected_packages": {
            name: {key: package[key] for key in package_keys}
            for name, package in modern_metadata["injected_packages"].items()
        },
        "pipx_metadata_version": metadata_version,
    }
    # written the way PipxMetadata.write() does, which would stamp the current metadata version instead
    with (venv_dir / "pipx_metadata.json").open("w", encoding="utf-8") as pipx_metadata_fh:
        json.dump(legacy_metadata, pipx_metadata_fh, indent=4, sort_keys=True, cls=JsonEncoderHandlesPath)


def create_package_info_ref(
    venv_name: str,
    package_name: str,
    pipx_venvs_dir: Path,
    *,
    include_apps: bool = True,
    app_paths_of_dependencies: dict[str, list[Path]] | None = None,
) -> PackageInfo:
    package: Final = PKG[package_name]
    man_pages: Final[list[str]] = package.get("man_pages", [])
    return PackageInfo(
        package=package_name,
        package_or_url=package["spec"],
        pip_args=[],
        include_apps=include_apps,
        include_dependencies=False,
        apps=package["apps"],
        app_paths=[pipx_venvs_dir / venv_name / ("Scripts" if WIN else "bin") / app for app in package["apps"]],
        apps_of_dependencies=package["apps_of_dependencies"],
        app_paths_of_dependencies=app_paths_of_dependencies or {},
        man_pages=man_pages,
        man_paths=[pipx_venvs_dir / venv_name / "share" / "man" / man_page for man_page in man_pages],
        man_pages_of_dependencies=package.get("man_pages_of_dependencies", []),
        man_paths_of_dependencies={},
        package_version=package["spec"].split("==")[-1],
    )


def assert_package_metadata(test_metadata: PackageInfo, ref_metadata: PackageInfo) -> None:
    assert test_metadata.package_version
    assert isinstance(test_metadata.apps, list)
    assert isinstance(test_metadata.app_paths, list)
    assert _sorted_apps(test_metadata) == _sorted_apps(ref_metadata)


def _sorted_apps(package: PackageInfo) -> PackageInfo:
    # pipx records apps in no fixed order
    return replace(
        package,
        apps=sorted(package.apps),
        app_paths=sorted(package.app_paths),
        apps_of_dependencies=sorted(package.apps_of_dependencies),
        app_paths_of_dependencies={key: sorted(value) for key, value in package.app_paths_of_dependencies.items()},
    )


def drop_extra_app(project: Path) -> None:
    pyproject: Final[Path] = project / "pyproject.toml"
    pyproject.write_text(
        pyproject
        .read_text(encoding="utf-8")
        .replace('version = "0.1.0"', 'version = "0.2.0"')
        .replace('scripts.empty-project-extra = "empty_project.main:cli"\n', ""),
        encoding="utf-8",
    )


def remove_venv_interpreter(venv_name: str) -> None:
    _, venv_python_path, _ = get_venv_paths(paths.CTX.venvs / venv_name)
    assert venv_python_path.is_file()
    venv_python_path.unlink()


SKIP_IF_WINDOWS: Final[pytest.MarkDecorator] = pytest.mark.skipif(WIN, reason="This behavior is undefined on Windows")


def write_wheel(
    directory: Path, name: str, version: str, requires: tuple[str, ...] = (), *, module_code: str = ""
) -> Path:
    dist_info: Final[str] = f"{name}-{version}.dist-info"
    members: Final[dict[str, str]] = {
        f"{name}.py": f"{module_code}VERSION = {version!r}\n",
        f"{dist_info}/METADATA": "".join([
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
            *(f"Requires-Dist: {requirement}\n" for requirement in requires),
        ]),
        f"{dist_info}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{dist_info}/entry_points.txt": f"[console_scripts]\n{name} = {name}:VERSION\n",
    }
    directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel := directory / f"{name}-{version}-py3-none-any.whl", "w") as archive:
        for member, content in members.items():
            archive.writestr(member, content)
        archive.writestr(
            f"{dist_info}/RECORD", "".join(f"{member},,\n" for member in [*members, f"{dist_info}/RECORD"])
        )
    return wheel


def write_dist_info(
    site_packages: Path, name: str, requires: list[str] | None = None, provides_extra: list[str] | None = None
) -> None:
    (dist_info := site_packages / f"{name}-1.0.dist-info").mkdir()
    (dist_info / "METADATA").write_text(
        "\n".join([
            f"Name: {name}",
            "Version: 1.0",
            *(f"Provides-Extra: {extra}" for extra in provides_extra or []),
            *(f"Requires-Dist: {requirement}" for requirement in requires or []),
        ]),
        encoding="utf-8",
    )


def module_version(venv_name: str) -> str:
    return subprocess.check_output(
        [Venv(paths.CTX.venvs / venv_name).python_path, "-c", f"import {venv_name}; print({venv_name}.VERSION)"],
        text=True,
    ).strip()


def file_or_symlink(path: Path) -> bool:
    # exists() is false for a broken symlink
    return path.exists() or path.is_symlink()


__all__ = [
    "LEGACY_MAIN_PACKAGE",
    "PACKAGE_CACHE_DIR_NAME",
    "PIPX_METADATA_LEGACY_VERSIONS",
    "SKIP_IF_WINDOWS",
    "WIN",
    "CurrentMetadata",
    "LegacyMetadata",
    "LegacyPackageInfo",
    "MakePylock",
    "app_name",
    "assert_package_metadata",
    "create_package_info_ref",
    "current_log_file",
    "drop_extra_app",
    "file_or_symlink",
    "mock_legacy_venv",
    "module_version",
    "pipx_subprocess_env",
    "remove_venv_interpreter",
    "run_pipx_cli",
    "unwrap_log_text",
    "write_dist_info",
    "write_wheel",
]
