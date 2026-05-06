from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import pytest

from pipx import backends, pipx_metadata_file
from pipx.backends import (
    KNOWN_BACKENDS,
    PIP,
    UV,
    assert_not_pip_under_uv,
    env_default_backend,
    find_uv_binary,
    resolve_backend_name,
)
from pipx.commands.run_uv import translate_pip_args_for_uv
from pipx.main import _validate_backend_available
from pipx.util import PipxError
from pipx.venv import Venv, reset_backend_override_warnings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class _BackendResolveKwargs(TypedDict, total=False):
    cli_value: str
    env_value: str
    metadata_value: str
    auto: bool


class _LegacyPackageInfo(TypedDict):
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


class _LegacyMetadata(TypedDict):
    main_package: _LegacyPackageInfo
    python_version: str
    source_interpreter: None
    venv_args: list[str]
    injected_packages: dict[str, _LegacyPackageInfo]
    pipx_metadata_version: str


class _CurrentMetadata(_LegacyMetadata):
    backend: str


def test_known_backends() -> None:
    assert KNOWN_BACKENDS == ("pip", "uv")


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty"),
        pytest.param("uv", "uv", id="uv"),
        pytest.param("  pip  ", "pip", id="trims-whitespace"),
    ],
)
def test_env_default_backend(monkeypatch: pytest.MonkeyPatch, env: str | None, expected: str | None) -> None:
    if env is None:
        monkeypatch.delenv("PIPX_DEFAULT_BACKEND", raising=False)
    else:
        monkeypatch.setenv("PIPX_DEFAULT_BACKEND", env)
    assert env_default_backend() == expected


@pytest.mark.parametrize(
    ("kwargs", "expected_name", "expected_source"),
    [
        pytest.param({"cli_value": "pip"}, "pip", "cli", id="cli-pip"),
        pytest.param({"cli_value": "uv"}, "uv", "cli", id="cli-uv"),
        pytest.param({"env_value": "pip"}, "pip", "env", id="env-pip"),
        pytest.param({"metadata_value": "uv"}, "uv", "metadata", id="metadata-uv"),
        pytest.param(
            {"cli_value": "pip", "env_value": "uv", "metadata_value": "uv"},
            "pip",
            "cli",
            id="cli-wins",
        ),
        # The headline bug fix: env must NOT override an existing venv's metadata.
        pytest.param(
            {"env_value": "uv", "metadata_value": "pip"},
            "pip",
            "metadata",
            id="metadata-locks-env-out",
        ),
        pytest.param({"env_value": "uv"}, "uv", "env", id="env-when-no-metadata"),
    ],
)
def test_resolve_backend_name_precedence(
    kwargs: _BackendResolveKwargs, expected_name: str, expected_source: str
) -> None:
    name, source = resolve_backend_name(**kwargs)
    assert (name, source) == (expected_name, expected_source)


def test_resolve_backend_name_rejects_unknown() -> None:
    with pytest.raises(PipxError, match="Unknown backend"):
        resolve_backend_name(cli_value="poetry")


def test_resolve_backend_name_auto_uv_available(mocker: MockerFixture) -> None:
    mocker.patch.object(backends, "find_uv_binary", return_value=(Path("/opt/uv"), "path"))
    assert resolve_backend_name() == (UV, "auto-path")


def test_resolve_backend_name_auto_no_uv(mocker: MockerFixture) -> None:
    mocker.patch.object(backends, "find_uv_binary", return_value=(None, "missing"))
    assert resolve_backend_name() == (PIP, "auto-pip")


def test_resolve_backend_name_auto_disabled(mocker: MockerFixture) -> None:
    mocker.patch.object(backends, "find_uv_binary", return_value=(Path("/opt/uv"), "path"))
    assert resolve_backend_name(auto=False) == (PIP, "auto-pip")


def test_find_uv_binary_prefers_bundled(mocker: MockerFixture, tmp_path: Path) -> None:
    bundled = tmp_path / "bundled-uv"
    bundled.write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", lambda: str(bundled))
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    # Stub bundled isn't a real uv, so bypass the launch probe.
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    binary, source = find_uv_binary()
    assert binary == bundled
    assert source == "bundled"


def test_find_uv_binary_skips_broken_bundled(mocker: MockerFixture, tmp_path: Path) -> None:
    bundled = tmp_path / "bundled-uv"
    bundled.write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", lambda: str(bundled))
    mocker.patch("pipx.backends.uv._binary_runs", return_value=False)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    binary, source = find_uv_binary()
    assert binary == Path("/usr/local/bin/uv")
    assert source == "path"


def test_find_uv_binary_falls_back_to_path(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    binary, source = find_uv_binary()
    assert binary == Path("/usr/local/bin/uv")
    assert source == "path"


def test_find_uv_binary_missing(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value=None)
    binary, source = find_uv_binary()
    assert binary is None
    assert source == "missing"


def test_find_uv_binary_is_cached(mocker: MockerFixture) -> None:
    # Self-contained cache reset: this test asserts hot-loop performance and
    # must not rely on the autouse fixture's reset already having run.
    find_uv_binary.cache_clear()
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    which_mock = mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    find_uv_binary()
    find_uv_binary()
    find_uv_binary()
    assert which_mock.call_count == 1


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param(["-q"], [], id="strip-quiet-short"),
        pytest.param(["--quiet"], [], id="strip-quiet-long"),
        pytest.param(
            ["--index-url", "https://example.com/simple"],
            ["--index-url", "https://example.com/simple"],
            id="index-url",
        ),
        pytest.param(
            ["--extra-index-url", "https://other.example/simple"],
            ["--extra-index-url", "https://other.example/simple"],
            id="extra-index",
        ),
        pytest.param(["--pre"], ["--prerelease=allow"], id="pre-to-prerelease"),
        pytest.param(["--index-url=https://example.com"], ["--index-url=https://example.com"], id="equals-form"),
    ],
)
def test_translate_pip_args_for_uv(pip_args: list[str], expected: list[str]) -> None:
    assert translate_pip_args_for_uv(pip_args) == expected


@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param(["--editable"], id="editable"),
        pytest.param(["-e"], id="editable-short"),
        pytest.param(["--no-build-isolation"], id="unknown-flag"),
        pytest.param(["--index-url"], id="missing-value"),
    ],
)
def test_translate_pip_args_for_uv_errors(pip_args: list[str]) -> None:
    with pytest.raises(PipxError):
        translate_pip_args_for_uv(pip_args)


def test_assert_not_pip_under_uv_blocks_pip_on_uv() -> None:
    with pytest.raises(PipxError, match="cannot be installed or exposed via the uv backend"):
        assert_not_pip_under_uv("pip", UV)


def test_assert_not_pip_under_uv_allows_pip_on_pip() -> None:
    assert_not_pip_under_uv("pip", PIP)  # does not raise


def test_assert_not_pip_under_uv_allows_other_packages_on_uv() -> None:
    assert_not_pip_under_uv("ruff", UV)  # does not raise


def test_metadata_round_trip_includes_backend(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    metadata = pipx_metadata_file.PipxMetadata(venv_dir, read=False)
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

    raw_payload = json.loads((venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).read_text())
    assert raw_payload["backend"] == "uv"

    reread = pipx_metadata_file.PipxMetadata(venv_dir)
    assert reread.backend == "uv"


def test_legacy_metadata_defaults_to_pip(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    legacy_payload: _LegacyMetadata = {
        "main_package": {
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
        },
        "python_version": "3.12",
        "source_interpreter": None,
        "venv_args": [],
        "injected_packages": {},
        "pipx_metadata_version": "0.5",
    }
    (venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).write_text(json.dumps(legacy_payload))

    metadata = pipx_metadata_file.PipxMetadata(venv_dir)
    assert metadata.backend == "pip"


def test_validate_backend_silent_on_env_uv_missing(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Diagnostic commands (``pipx environment``/``list``) must keep working
    # without a startup warning that would later contradict the actual error
    # from ``UvBackend.__init__``.
    # Patch both the source and the package-level re-export — either branch
    # poisons the test if only one is mocked.
    mocker.patch.object(backends, "find_uv_binary", return_value=(None, "missing"))
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(None, "missing"))
    monkeypatch.setenv("PIPX_DEFAULT_BACKEND", "uv")
    caplog.set_level("WARNING", logger="pipx.main")

    _validate_backend_available(cli_backend=None, env_backend="uv")

    assert not any("uv" in rec.message.lower() for rec in caplog.records)


def test_validate_backend_raises_on_cli_uv_missing(mocker: MockerFixture) -> None:
    mocker.patch.object(backends, "find_uv_binary", return_value=(None, "missing"))
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(None, "missing"))
    with pytest.raises(PipxError, match="uv' executable could not be found"):
        _validate_backend_available(cli_backend="uv", env_backend=None)


def test_backend_override_warning_dedups_per_venv(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # ``upgrade-all --backend uv`` against many pip-backed venvs would
    # otherwise emit a multi-line block per Venv construction.
    venv_dir = tmp_path / "demo"
    venv_dir.mkdir()
    metadata_payload: _CurrentMetadata = {
        "main_package": {
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
        },
        "python_version": "3.12",
        "source_interpreter": None,
        "venv_args": [],
        "injected_packages": {},
        "backend": "pip",
        "pipx_metadata_version": "0.6",
    }
    (venv_dir / pipx_metadata_file.PIPX_INFO_FILENAME).write_text(json.dumps(metadata_payload))

    reset_backend_override_warnings()
    caplog.set_level("WARNING", logger="pipx.venv")

    Venv(venv_dir, backend="uv")
    Venv(venv_dir, backend="uv")
    Venv(venv_dir, backend="uv")

    warnings = [rec for rec in caplog.records if "Ignoring --backend=uv" in rec.message]
    assert len(warnings) == 1
