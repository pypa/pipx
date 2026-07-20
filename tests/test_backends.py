from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypedDict

import pytest

from pipx import backends, pipx_metadata_file
from pipx.backends import (
    KNOWN_BACKENDS,
    PIP,
    UV,
    OutdatedPackage,
    assert_not_pip_under_uv,
    env_default_backend,
    find_uv_binary,
    resolve_backend_name,
)
from pipx.backends.pip import PipBackend
from pipx.backends.uv import UvBackend, resolve_uv_binary
from pipx.commands.run_uv import translate_pip_args_for_uv
from pipx.constants import PIPX_SHARED_PTH
from pipx.main import (
    _validate_backend_available,  # ruff:ignore[import-private-name]  # test exercises private helper, no public API
)
from pipx.util import PipxError
from pipx.venv import Venv, reset_backend_override_warnings
from pipx.venv_inspect import list_not_required_packages

if TYPE_CHECKING:
    from unittest.mock import MagicMock

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


def _write_dist_info(
    site_packages: Path, name: str, requires: list[str] | None = None, provides_extra: list[str] | None = None
) -> None:
    dist_info = site_packages / f"{name}-1.0.dist-info"
    dist_info.mkdir()
    metadata = [f"Name: {name}", "Version: 1.0"]
    metadata += [f"Provides-Extra: {extra}" for extra in provides_extra or []]
    metadata += [f"Requires-Dist: {requirement}" for requirement in requires or []]
    (dist_info / "METADATA").write_text("\n".join(metadata), encoding="utf-8")


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
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", return_value=str(bundled))
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    # Stub bundled isn't a real uv, so bypass the launch probe.
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    binary, source = find_uv_binary()
    assert binary == bundled
    assert source == "bundled"


def test_find_uv_binary_skips_broken_bundled(mocker: MockerFixture, tmp_path: Path) -> None:
    bundled = tmp_path / "bundled-uv"
    bundled.write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", return_value=str(bundled))
    mocker.patch("pipx.backends.uv._binary_runs", side_effect=lambda candidate: candidate != bundled)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    binary, source = find_uv_binary()
    assert binary == Path("/usr/local/bin/uv")
    assert source == "path"


def test_find_uv_binary_falls_back_to_path(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    binary, source = find_uv_binary()
    assert binary == Path("/usr/local/bin/uv")
    assert source == "path"


def test_find_uv_binary_skips_broken_path(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("pipx.backends.uv._binary_runs", return_value=False)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    binary, source = find_uv_binary()
    assert binary is None
    assert source == "missing"


def test_find_uv_binary_probe_survives_a_hanging_path_uv(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["uv", "--version"], timeout=10),
    )
    binary, source = find_uv_binary()
    assert binary is None
    assert source == "missing"


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
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    which_mock = mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    find_uv_binary()
    find_uv_binary()
    find_uv_binary()
    assert which_mock.call_count == 1


def test_resolve_uv_binary_reports_a_hanging_version_probe(mocker: MockerFixture) -> None:
    binary: Final[Path] = Path("/usr/local/bin/uv")
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=[str(binary), "--version"], timeout=10),
    )

    with pytest.raises(PipxError, match="Could not run"):
        resolve_uv_binary()


def test_uv_backend_rejects_pre_cooldown_version(mocker: MockerFixture) -> None:
    binary: Final[Path] = Path("/usr/local/bin/uv")
    mocker.patch("pipx.backends.uv.resolve_uv_binary", return_value=binary)
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess([str(binary), "--version"], 0, stdout="uv 0.9.16", stderr=""),
    )

    with pytest.raises(PipxError, match=r"uv>=0\.9\.17"):
        UvBackend()


@pytest.mark.parametrize("backend_name", [pytest.param(PIP, id="pip"), pytest.param(UV, id="uv")])
def test_backend_verbose_install_streams_output(backend_name: str, tmp_path: Path, mocker: MockerFixture) -> None:
    binary: Final[Path] = tmp_path / "uv"
    mocker.patch("pipx.backends.uv.resolve_uv_binary", return_value=binary)
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess([str(binary), "--version"], 0, stdout="uv 0.11.28", stderr=""),
    )
    run_subprocess: Final[MagicMock] = mocker.patch(
        f"pipx.backends.{backend_name}.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    (UvBackend() if backend_name == UV else PipBackend()).install(
        venv_root=tmp_path,
        venv_python=venv_python,
        requirements=["demo"],
        pip_args=[],
        verbose=True,
    )

    expected_command: Final[list[str | Path]] = (
        [str(venv_python), "-m", "pip", "--no-input", "install", "--progress-bar=on", "demo"]
        if backend_name == PIP
        else [binary, "pip", "install", "--python", str(venv_python), "--verbose", "demo"]
    )
    assert (run_subprocess.call_args.args[0], run_subprocess.call_args.kwargs["stream_output"]) == (
        expected_command,
        True,
    )


@pytest.mark.parametrize(
    ("backend_name", "progress", "flags", "streams"),
    [
        pytest.param(PIP, True, ["--progress-bar=on"], True, id="pip-progress"),
        pytest.param(PIP, False, [], False, id="pip-plain"),
        # uv hides its bar under --verbose and under --quiet, so progress mode passes neither
        pytest.param(UV, True, [], True, id="uv-progress"),
        pytest.param(UV, False, ["--quiet"], False, id="uv-plain"),
    ],
)
def test_backend_install_draws_progress_without_verbose(  # ruff:ignore[too-many-positional-arguments]  # pytest injects fixtures by name
    backend_name: str,
    progress: bool,
    flags: list[str],
    streams: bool,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    binary: Final[Path] = tmp_path / "uv"
    mocker.patch("pipx.backends.uv.resolve_uv_binary", return_value=binary)
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess([str(binary), "--version"], 0, stdout="uv 0.11.28", stderr=""),
    )
    run_subprocess: Final[MagicMock] = mocker.patch(
        f"pipx.backends.{backend_name}.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    (UvBackend() if backend_name == UV else PipBackend()).install(
        venv_root=tmp_path,
        venv_python=venv_python,
        requirements=["demo"],
        pip_args=[],
        progress=progress,
    )

    expected_command: Final[list[str | Path]] = (
        [str(venv_python), "-m", "pip", "--no-input", "install", *flags, "demo"]
        if backend_name == PIP
        else [binary, "pip", "install", "--python", str(venv_python), *flags, "demo"]
    )
    assert (run_subprocess.call_args.args[0], run_subprocess.call_args.kwargs["stream_output"]) == (
        expected_command,
        streams,
    )


@pytest.mark.parametrize(
    ("progress", "expected_no_progress"),
    [
        pytest.param(True, None, id="progress-leaves-user-env"),
        pytest.param(False, "1", id="quiet-silences-uv-bar"),
    ],
)
def test_uv_install_gates_progress_bar_via_env(
    progress: bool,
    expected_no_progress: str | None,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    binary: Final[Path] = tmp_path / "uv"
    mocker.patch("pipx.backends.uv.resolve_uv_binary", return_value=binary)
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess([str(binary), "--version"], 0, stdout="uv 0.11.28", stderr=""),
    )
    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.backends.uv.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    UvBackend().install(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        requirements=["demo"],
        pip_args=[],
        progress=progress,
    )

    assert run_subprocess.call_args.kwargs["env_overrides"] == {
        "VIRTUAL_ENV": None,
        **({"UV_NO_PROGRESS": expected_no_progress} if expected_no_progress is not None else {}),
    }


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
        pytest.param(["--no-binary", ":all:"], ["--no-binary"], id="no-binary-all"),
        pytest.param(
            ["--no-binary", "one,two"],
            ["--no-binary-package", "one", "--no-binary-package", "two"],
            id="no-binary-packages",
        ),
        pytest.param(["--no-binary=:none:"], [], id="no-binary-none"),
        pytest.param(["--only-binary", ":all:"], ["--no-build"], id="only-binary-all"),
        pytest.param(
            ["--only-binary=one,two"],
            ["--no-build-package", "one", "--no-build-package", "two"],
            id="only-binary-packages",
        ),
        pytest.param(
            ["--trusted-host", "packages.example"],
            ["--allow-insecure-host", "packages.example"],
            id="trusted-host",
        ),
        pytest.param(
            ["--trusted-host=packages.example"],
            ["--allow-insecure-host=packages.example"],
            id="trusted-host-equals",
        ),
    ],
)
def test_translate_pip_args_for_uv(pip_args: list[str], expected: list[str]) -> None:
    assert translate_pip_args_for_uv(pip_args) == expected


@pytest.mark.parametrize(
    ("pip_args", "match"),
    [
        pytest.param(["--editable"], "is not supported", id="editable"),
        pytest.param(["-e"], "is not supported", id="editable-short"),
        pytest.param(
            ["--no-build-isolation"],
            "contains '--no-build-isolation', which has no",
            id="unknown-flag",
        ),
        pytest.param(["--no-deps"], "contains '--no-deps', which has no", id="no-deps"),
        pytest.param(["--no-binary="], "Invalid value", id="empty-no-binary"),
        pytest.param(["--index-url"], "Missing value", id="missing-value"),
    ],
)
def test_translate_pip_args_for_uv_errors(pip_args: list[str], match: str) -> None:
    with pytest.raises(PipxError, match=match):
        translate_pip_args_for_uv(pip_args)


def test_assert_not_pip_under_uv_blocks_pip_on_uv() -> None:
    with pytest.raises(PipxError, match="cannot be installed or exposed via the uv backend"):
        assert_not_pip_under_uv("pip", UV)


def test_assert_not_pip_under_uv_allows_pip_on_pip() -> None:
    assert_not_pip_under_uv("pip", PIP)  # does not raise


def test_assert_not_pip_under_uv_allows_other_packages_on_uv() -> None:
    assert_not_pip_under_uv("ruff", UV)  # does not raise


def test_uv_list_installed_not_required_uses_distribution_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    _write_dist_info(site_packages, "root-package")
    _write_dist_info(site_packages, "top-package", ["child-package>=1"])
    _write_dist_info(site_packages, "child-package")

    def fail_run_subprocess(*_args: object, **_kwargs: object) -> None:
        pytest.fail("uv pip list should not be invoked with --not-required")

    monkeypatch.setattr("pipx.backends.uv.run_subprocess", fail_run_subprocess)
    monkeypatch.setattr(
        "pipx.venv_inspect.fetch_info_in_venv",
        lambda _venv_python: ([str(site_packages)], {}, "Python 3.13.0"),
        raising=False,
    )

    backend = UvBackend.__new__(UvBackend)
    backend._binary = tmp_path / "uv"  # ruff:ignore[private-member-access]  # constructing backend bypasses __init__ to isolate list_installed

    assert backend.list_installed(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        not_required=True,
    ) == {"root-package", "top-package"}


@pytest.mark.parametrize("backend_name", [pytest.param(PIP, id="pip"), pytest.param(UV, id="uv")])
def test_backend_list_outdated_forwards_index_settings(
    backend_name: str, tmp_path: Path, mocker: MockerFixture
) -> None:
    backend: PipBackend | UvBackend
    if backend_name == PIP:
        backend = PipBackend()
        expected_command: list[str | Path] = [
            str(tmp_path / "bin" / "python"),
            "-m",
            "pip",
            "list",
            "--outdated",
            "--format=json",
            "--index-url",
            "https://index.example/simple",
        ]
    else:
        mocker.patch(
            "pipx.backends.uv.find_uv_binary",
            autospec=True,
            return_value=(tmp_path / "uv", "path"),
        )
        mocker.patch(
            "pipx.backends.uv.subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="uv 0.10.0", stderr=""),
        )
        backend = UvBackend()
        expected_command = [
            tmp_path / "uv",
            "pip",
            "list",
            "--python",
            str(tmp_path / "bin" / "python"),
            "--quiet",
            "--outdated",
            "--format=json",
            "--index-url",
            "https://index.example/simple",
        ]
    run_subprocess = mocker.patch(
        f"pipx.backends.{'pip' if backend_name == PIP else 'uv'}.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='[{"name":"demo","version":"1","latest_version":"2"}]',
            stderr="",
        ),
    )

    result = backend.list_outdated(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        index_args=["--index-url", "https://index.example/simple"],
    )

    assert (result, run_subprocess.call_args.args[0]) == (
        (OutdatedPackage(name="demo", version="1", latest_version="2"),),
        expected_command,
    )


@pytest.mark.parametrize(
    ("backend_type", "expected"),
    [
        pytest.param(PipBackend, "--uploaded-prior-to", id="pip"),
        pytest.param(UvBackend, "--exclude-newer", id="uv"),
    ],
)
def test_backend_cooldown_args(
    backend_type: type[PipBackend | UvBackend],
    expected: str,
) -> None:
    assert (
        backend_type.cooldown_args(None),
        backend_type.cooldown_args(0),
        backend_type.cooldown_args(7),
    ) == ([], [], [expected, "P7D"])


def test_list_not_required_packages_treats_extra_dependencies_as_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # ``child-package`` is required only via ``top-package``'s ``extra == "cli"`` dependency; it must
    # still be reported as required (not removable) while top-package stays installed.
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    _write_dist_info(site_packages, "top-package", ['child-package>=1; extra == "cli"'], provides_extra=["cli"])
    _write_dist_info(site_packages, "child-package")

    monkeypatch.setattr(
        "pipx.venv_inspect.fetch_info_in_venv",
        lambda _venv_python: ([str(site_packages)], {}, "Python 3.13.0"),
        raising=False,
    )

    assert list_not_required_packages(tmp_path / "bin" / "python") == {"top-package"}


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


def test_metadata_version_order_for_shared_libs(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    site_packages = venv_dir / "lib/python/site-packages"
    site_packages.mkdir(parents=True)
    (site_packages / PIPX_SHARED_PTH).touch()
    venv = Venv(venv_dir)
    venv.pipx_metadata.read_metadata_version = "0.10"
    venv.pipx_metadata.backend = UV

    assert venv.uses_shared_libs is False


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
