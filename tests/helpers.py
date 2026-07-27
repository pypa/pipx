from __future__ import annotations

import json
import re
import sys
import sysconfig
from dataclasses import replace
from pathlib import Path
from typing import Any, Final
from unittest import mock

import pytest
from packaging.utils import canonicalize_name

from package_info import PKG
from pipx import constants, main, paths, pipx_metadata_file, util

WIN = sys.platform.startswith("win")

# Mirrors scripts/test_packages_support.py: free-threaded builds seed a cache of cp3XXt wheels separate from the
# same-version GIL build's directory.
PACKAGE_CACHE_DIR_NAME: Final[str] = (
    f"{sys.version_info[0]}.{sys.version_info[1]}{'t' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''}"
)

PIPX_METADATA_LEGACY_VERSIONS = [None, "0.1", "0.2", "0.3"]


class _UnknownMetadataVersionError(Exception):
    """A test requested a pipx metadata version the mock helpers don't know."""


MOCK_PIPXMETADATA_0_1: dict[str, Any] = {
    "main_package": None,
    "python_version": None,
    "venv_args": [],
    "injected_packages": {},
    "pipx_metadata_version": "0.1",
}

MOCK_PIPXMETADATA_0_2: dict[str, Any] = {
    "main_package": None,
    "python_version": None,
    "venv_args": [],
    "injected_packages": {},
    "pipx_metadata_version": "0.2",
}

MOCK_PIPXMETADATA_0_3: dict[str, Any] = {
    "main_package": None,
    "python_version": None,
    "venv_args": [],
    "injected_packages": {},
    "pipx_metadata_version": "0.3",
    "man_pages": [],
    "man_paths": [],
    "man_pages_of_dependencies": [],
    "man_paths_of_dependencies": {},
}

MOCK_PACKAGE_INFO_0_1: dict[str, Any] = {
    "package": None,
    "package_or_url": None,
    "pip_args": [],
    "include_dependencies": False,
    "include_apps": True,
    "apps": [],
    "app_paths": [],
    "apps_of_dependencies": [],
    "app_paths_of_dependencies": {},
    "package_version": "",
}

MOCK_PACKAGE_INFO_0_2: dict[str, Any] = {
    "package": None,
    "package_or_url": None,
    "pip_args": [],
    "include_dependencies": False,
    "include_apps": True,
    "apps": [],
    "app_paths": [],
    "apps_of_dependencies": [],
    "app_paths_of_dependencies": {},
    "package_version": "",
    "suffix": "",
}


def app_name(app: str) -> str:
    return f"{app}.exe" if WIN else app


def run_pipx_cli(pipx_args: list[str]) -> int:
    with mock.patch.object(sys, "argv", ["pipx", *pipx_args]):
        return main.cli()


def unwrap_log_text(log_text: str) -> str:
    """Remove line-break + indent space from log messages

    Captured log lines always start with the 'severity' so if a line starts
    with any spaces assume it is due to an indented pipx wrapped message.
    """

    return re.sub(r"\n\s+", " ", log_text)


def _mock_legacy_package_info(modern_package_info: dict[str, Any], metadata_version: str) -> dict[str, Any]:
    if metadata_version in {"0.2", "0.3"}:
        mock_package_info_template = MOCK_PACKAGE_INFO_0_2
    elif metadata_version == "0.1":
        mock_package_info_template = MOCK_PACKAGE_INFO_0_1
    else:
        msg = f"Internal Test Error: Unknown metadata_version={metadata_version}"
        raise _UnknownMetadataVersionError(msg)

    mock_package_info = {}
    for key in mock_package_info_template:
        mock_package_info[key] = modern_package_info[key]

    return mock_package_info


def mock_legacy_venv(venv_name: str, metadata_version: str | None = None) -> None:
    """Convert a venv installed with the most recent pipx to look like
    one with a previous metadata version.
    metadata_version=None refers to no metadata file (pipx pre-0.15.0.0)
    """
    venv_dir = Path(paths.ctx.venvs) / canonicalize_name(venv_name)

    if metadata_version == "0.4":
        # Current metadata version, do nothing
        return
    if metadata_version == "0.3":
        mock_pipx_metadata_template = MOCK_PIPXMETADATA_0_3
    elif metadata_version == "0.2":
        mock_pipx_metadata_template = MOCK_PIPXMETADATA_0_2
    elif metadata_version == "0.1":
        mock_pipx_metadata_template = MOCK_PIPXMETADATA_0_1
    elif metadata_version is None:
        # No metadata
        Path(venv_dir / "pipx_metadata.json").unlink()
        return
    else:
        msg = f"Internal Test Error: Unknown metadata_version={metadata_version}"
        raise _UnknownMetadataVersionError(msg)

    modern_metadata = pipx_metadata_file.PipxMetadata(venv_dir).to_dict()

    # Convert to mock old metadata
    mock_pipx_metadata: dict[str, Any] = {}
    for key in mock_pipx_metadata_template:
        if key == "main_package":
            mock_pipx_metadata[key] = _mock_legacy_package_info(modern_metadata[key], metadata_version=metadata_version)
        if key == "injected_packages":
            mock_pipx_metadata[key] = {}
            for injected in modern_metadata[key]:
                mock_pipx_metadata[key][injected] = _mock_legacy_package_info(
                    modern_metadata[key][injected], metadata_version=metadata_version
                )
        else:
            mock_pipx_metadata[key] = modern_metadata.get(key)
    mock_pipx_metadata["pipx_metadata_version"] = mock_pipx_metadata_template["pipx_metadata_version"]

    # replicate pipx_metadata_file.PipxMetadata.write()
    with Path(venv_dir / "pipx_metadata.json").open("w", encoding="utf-8") as pipx_metadata_fh:
        json.dump(
            mock_pipx_metadata,
            pipx_metadata_fh,
            indent=4,
            sort_keys=True,
            cls=pipx_metadata_file.JsonEncoderHandlesPath,
        )


def create_package_info_ref(
    venv_name: str,
    package_name: str,
    pipx_venvs_dir: Path,
    *,
    pip_args: list[str] | None = None,
    include_apps: bool = True,
    include_dependencies: bool = False,
    app_paths_of_dependencies: dict[str, list[Path]] | None = None,
    man_paths_of_dependencies: dict[str, list[Path]] | None = None,
) -> pipx_metadata_file.PackageInfo:
    """Create reference PackageInfo to check against

    Overridable fields to be used in field_overrides:
        pip_args (default: [])
        include_apps (default: True)
        include_dependencies (default: False)
        app_paths_of_dependencies (default: {})
    """
    venv_bin_dir = "Scripts" if constants.WINDOWS else "bin"
    return pipx_metadata_file.PackageInfo(
        package=package_name,
        package_or_url=PKG[package_name]["spec"],
        pip_args=pip_args if pip_args is not None else [],
        include_apps=include_apps,
        include_dependencies=include_dependencies,
        apps=PKG[package_name]["apps"],
        app_paths=[pipx_venvs_dir / venv_name / venv_bin_dir / app for app in PKG[package_name]["apps"]],
        apps_of_dependencies=PKG[package_name]["apps_of_dependencies"],
        app_paths_of_dependencies=app_paths_of_dependencies if app_paths_of_dependencies is not None else {},
        man_pages=PKG[package_name].get("man_pages", []),
        man_paths=[
            pipx_venvs_dir / venv_name / "share" / "man" / man_page
            for man_page in PKG[package_name].get("man_pages", [])
        ],
        man_pages_of_dependencies=PKG[package_name].get("man_pages_of_dependencies", []),
        man_paths_of_dependencies=man_paths_of_dependencies if man_paths_of_dependencies is not None else {},
        package_version=PKG[package_name]["spec"].split("==")[-1],
    )


def assert_package_metadata(
    test_metadata: pipx_metadata_file.PackageInfo,
    ref_metadata: pipx_metadata_file.PackageInfo,
) -> None:
    # only compare sorted versions of apps, app_paths so order is not important

    assert test_metadata.package_version
    assert isinstance(test_metadata.apps, list)
    assert isinstance(test_metadata.app_paths, list)

    test_metadata_replaced = replace(
        test_metadata,
        apps=sorted(test_metadata.apps),
        app_paths=sorted(test_metadata.app_paths),
        apps_of_dependencies=sorted(test_metadata.apps_of_dependencies),
        app_paths_of_dependencies={
            key: sorted(value) for key, value in test_metadata.app_paths_of_dependencies.items()
        },
    )
    ref_metadata_replaced = replace(
        ref_metadata,
        apps=sorted(ref_metadata.apps),
        app_paths=sorted(ref_metadata.app_paths),
        apps_of_dependencies=sorted(ref_metadata.apps_of_dependencies),
        app_paths_of_dependencies={key: sorted(value) for key, value in ref_metadata.app_paths_of_dependencies.items()},
    )
    assert test_metadata_replaced == ref_metadata_replaced


def remove_venv_interpreter(venv_name: str) -> None:
    _, venv_python_path, _ = util.get_venv_paths(paths.ctx.venvs / venv_name)
    assert venv_python_path.is_file()
    venv_python_path.unlink()
    assert not venv_python_path.is_file()


skip_if_windows = pytest.mark.skipif(sys.platform.startswith("win"), reason="This behavior is undefined on Windows")


# The tests exercise the pinned index snapshot the mocked_github_api fixture serves, so whether a build exists for the
# running interpreter is a property of that snapshot; the skip revives the tests when a refreshed snapshot carries one.
_RUNNING_CPYTHON: Final[str] = f"cpython-{sys.version_info[0]}.{sys.version_info[1]}."
skip_if_no_standalone_python = pytest.mark.skipif(
    not any(
        _RUNNING_CPYTHON in link
        for link, _ in json.loads(
            (Path(__file__).parents[1] / "testdata" / "standalone_python_index_20250818.json").read_text("utf-8")
        )["releases"]
    ),
    reason=f"the pinned python-build-standalone index has no {_RUNNING_CPYTHON}* build",
)
