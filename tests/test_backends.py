from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import write_dist_info
from pipx import paths
from pipx.backends import registry
from pipx.backends._base import KNOWN_BACKENDS, PIP, UV, OutdatedPackage  # ruff:ignore[import-private-name]  # no public home
from pipx.backends.pip import PipBackend
from pipx.backends.registry import assert_not_pip_under_uv, env_default_backend, resolve_backend_name
from pipx.backends.uv import UvBackend, find_uv_binary, resolve_uv_binary
from pipx.constants import WINDOWS
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


def test_known_backends() -> None:
    assert KNOWN_BACKENDS == ("pip", "uv")


def test_env_default_backend_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIPX_DEFAULT_BACKEND", raising=False)
    assert env_default_backend() is None


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param("", None, id="empty"),
        pytest.param("uv", "uv", id="uv"),
        pytest.param("  pip  ", "pip", id="trims-whitespace"),
    ],
)
def test_env_default_backend(monkeypatch: pytest.MonkeyPatch, env: str, expected: str | None) -> None:
    monkeypatch.setenv("PIPX_DEFAULT_BACKEND", env)
    assert env_default_backend() == expected


@pytest.mark.parametrize(
    ("cli_value", "env_value", "metadata_value", "expected"),
    [
        pytest.param("pip", None, None, ("pip", "cli"), id="cli-pip"),
        pytest.param("uv", None, None, ("uv", "cli"), id="cli-uv"),
        pytest.param(None, "pip", None, ("pip", "env"), id="env-pip"),
        pytest.param(None, None, "uv", ("uv", "metadata"), id="metadata-uv"),
        pytest.param("pip", "uv", "uv", ("pip", "cli"), id="cli-wins"),
        pytest.param(None, "uv", "pip", ("pip", "metadata"), id="metadata-locks-env-out"),
        pytest.param(None, "uv", None, ("uv", "env"), id="env-when-no-metadata"),
    ],
)
def test_resolve_backend_name_precedence(
    cli_value: str | None, env_value: str | None, metadata_value: str | None, expected: tuple[str, str]
) -> None:
    assert resolve_backend_name(cli_value=cli_value, env_value=env_value, metadata_value=metadata_value) == expected


def test_resolve_backend_name_rejects_unknown() -> None:
    with pytest.raises(PipxError, match="Unknown backend"):
        resolve_backend_name(cli_value="poetry", env_value=None)


@pytest.fixture
def path_uv_reports(mocker: MockerFixture) -> Callable[[str], None]:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")

    def report(version: str) -> None:
        mocker.patch(
            "pipx.backends.uv.subprocess.run",
            return_value=subprocess.CompletedProcess(["uv", "--version"], 0, stdout=f"uv {version}", stderr=""),
        )

    return report


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        pytest.param("0.9.17", (UV, "auto-path"), id="supported"),
        pytest.param("0.5.0", (PIP, "auto-pip"), id="too-old"),
    ],
)
def test_resolve_backend_name_auto_path_uv(
    path_uv_reports: Callable[[str], None], version: str, expected: tuple[str, str]
) -> None:
    path_uv_reports(version)
    assert resolve_backend_name(env_value=None) == expected


def test_resolve_backend_name_auto_skips_too_old_bundled_uv(
    path_uv_reports: Callable[[str], None], mocker: MockerFixture, tmp_path: Path
) -> None:
    path_uv_reports("0.5.0")
    (bundled := tmp_path / "uv").write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", return_value=str(bundled))
    mocker.patch("shutil.which", return_value=None)
    assert resolve_backend_name(env_value=None) == (PIP, "auto-pip")


def test_resolve_backend_name_auto_warns_once_about_too_old_uv(
    path_uv_reports: Callable[[str], None], caplog: pytest.LogCaptureFixture
) -> None:
    path_uv_reports("0.5.0")
    resolve_backend_name(env_value=None)
    resolve_backend_name(env_value=None)
    assert [record.getMessage() for record in caplog.records if record.levelname == "WARNING"] == [
        (
            f"Skipping uv 0.5.0 at {Path('/usr/local/bin/uv')} since pipx needs uv>=0.9.17; using pip. "
            "Upgrade uv, or set PIPX_DEFAULT_BACKEND=pip to silence this."
        )
    ]


@pytest.mark.parametrize(
    ("cli_value", "env_value", "metadata_value", "expected"),
    [
        pytest.param("uv", None, None, (UV, "cli"), id="cli"),
        pytest.param(None, "uv", None, (UV, "env"), id="env"),
        pytest.param(None, None, "uv", (UV, "metadata"), id="metadata"),
    ],
)
def test_resolve_backend_name_keeps_explicit_uv_when_too_old(
    path_uv_reports: Callable[[str], None],
    cli_value: str | None,
    env_value: str | None,
    metadata_value: str | None,
    expected: tuple[str, str],
) -> None:
    path_uv_reports("0.5.0")
    assert resolve_backend_name(cli_value=cli_value, env_value=env_value, metadata_value=metadata_value) == expected


def test_resolve_backend_name_auto_no_uv(mocker: MockerFixture) -> None:
    mocker.patch.object(registry, "find_uv_binary", return_value=(None, "missing"))
    assert resolve_backend_name(env_value=None) == (PIP, "auto-pip")


def test_resolve_backend_name_auto_disabled(mocker: MockerFixture) -> None:
    mocker.patch.object(registry, "find_uv_binary", return_value=(Path("/opt/uv"), "path"))
    assert resolve_backend_name(env_value=None, auto=False) == (PIP, "auto-pip")


def test_find_uv_binary_prefers_bundled(mocker: MockerFixture, tmp_path: Path) -> None:
    (bundled := tmp_path / "bundled-uv").write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", return_value=str(bundled))
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    # the stub bundled file is not a real uv, so bypass the launch probe
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    assert find_uv_binary() == (bundled, "bundled")


def test_find_uv_binary_skips_broken_bundled(mocker: MockerFixture, tmp_path: Path) -> None:
    (bundled := tmp_path / "bundled-uv").write_text("")
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", return_value=str(bundled))
    mocker.patch("pipx.backends.uv._binary_runs", side_effect=lambda candidate: candidate != bundled)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    assert find_uv_binary() == (Path("/usr/local/bin/uv"), "path")


@pytest.mark.parametrize(
    ("runs", "expected"),
    [
        pytest.param(True, (Path("/usr/local/bin/uv"), "path"), id="falls-back-to-path"),
        pytest.param(False, (None, "missing"), id="skips-broken-path"),
    ],
)
def test_find_uv_binary_path_candidate(mocker: MockerFixture, runs: bool, expected: tuple[Path | None, str]) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("pipx.backends.uv._binary_runs", return_value=runs)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    assert find_uv_binary() == expected


def test_find_uv_binary_probe_survives_a_hanging_path_uv(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["uv", "--version"], timeout=10),
    )
    assert find_uv_binary() == (None, "missing")


def test_find_uv_binary_missing(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value=None)
    assert find_uv_binary() == (None, "missing")


def test_find_uv_binary_is_cached(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("pipx.backends.uv._binary_runs", return_value=True)
    which_mock: Final[MagicMock] = mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    find_uv_binary()
    find_uv_binary()
    find_uv_binary()
    assert which_mock.call_count == 1


def test_resolve_uv_binary_runs_uv_version_once(mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.uv._FIND_UV_BIN_FROM_EXTRA", None)
    mocker.patch("shutil.which", return_value="/usr/local/bin/uv")
    run: Final[MagicMock] = mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess(["uv", "--version"], 0, stdout="uv 0.11.28", stderr=""),
    )

    resolve_uv_binary()

    assert run.call_count == 1


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


@pytest.fixture
def uv_binary(tmp_path: Path, mocker: MockerFixture) -> Path:
    binary: Final[Path] = tmp_path / "uv"
    mocker.patch("pipx.backends.uv.resolve_uv_binary", return_value=binary)
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(binary, "path"))
    mocker.patch(
        "pipx.backends.uv.subprocess.run",
        return_value=subprocess.CompletedProcess([str(binary), "--version"], 0, stdout="uv 0.11.28", stderr=""),
    )
    return binary


@pytest.fixture
def uv_run_subprocess(
    uv_binary: Path,  # ruff:ignore[unused-function-argument]  # UvBackend() must find the patched uv
    mocker: MockerFixture,
) -> MagicMock:
    return mocker.patch(
        "pipx.backends.uv.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )


@pytest.fixture
def pip_run_subprocess(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )


@pytest.mark.parametrize(
    ("verbose", "flags"),
    [pytest.param(True, ["--progress-bar=on"], id="verbose-streams"), pytest.param(False, [], id="quiet-captures")],
)
def test_pip_backend_install_streams_output_only_when_verbose(
    verbose: bool, flags: list[str], tmp_path: Path, pip_run_subprocess: MagicMock
) -> None:
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    PipBackend().install(
        venv_root=tmp_path, venv_python=venv_python, requirements=["demo"], pip_args=[], verbose=verbose
    )

    assert (pip_run_subprocess.call_args.args[0], pip_run_subprocess.call_args.kwargs["stream_output"]) == (
        [str(venv_python), "-m", "pip", "--no-input", "install", *flags, "demo"],
        verbose,
    )


@pytest.mark.parametrize(
    ("verbose", "flag"),
    [pytest.param(True, "--verbose", id="verbose-streams"), pytest.param(False, "--quiet", id="quiet-captures")],
)
def test_uv_backend_install_streams_output_only_when_verbose(
    verbose: bool, flag: str, tmp_path: Path, uv_run_subprocess: MagicMock
) -> None:
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    UvBackend().install(
        venv_root=tmp_path, venv_python=venv_python, requirements=["demo"], pip_args=[], verbose=verbose
    )

    assert (uv_run_subprocess.call_args.args[0], uv_run_subprocess.call_args.kwargs["stream_output"]) == (
        [tmp_path / "uv", "pip", "install", "--python", str(venv_python), flag, "demo"],
        verbose,
    )


def test_uv_install_rejects_recorded_empty_index(tmp_path: Path, uv_run_subprocess: MagicMock) -> None:
    with pytest.raises(PipxError, match=r"^--index-url is empty"):
        UvBackend().install(
            venv_root=tmp_path,
            venv_python=tmp_path / "bin" / "python",
            requirements=["demo"],
            pip_args=["--index-url="],
            verbose=False,
        )
    uv_run_subprocess.assert_not_called()


def test_uv_list_outdated_rejects_recorded_empty_index(tmp_path: Path, uv_run_subprocess: MagicMock) -> None:
    with pytest.raises(PipxError, match=r"^--default-index is empty"):
        UvBackend().list_outdated(
            venv_root=tmp_path, venv_python=tmp_path / "bin" / "python", index_args=["--default-index="], exclude=[]
        )
    uv_run_subprocess.assert_not_called()


def test_uv_install_silences_progress_bar(tmp_path: Path, uv_run_subprocess: MagicMock) -> None:
    UvBackend().install(
        venv_root=tmp_path, venv_python=tmp_path / "bin" / "python", requirements=["demo"], pip_args=[], verbose=False
    )

    assert uv_run_subprocess.call_args.kwargs["env_overrides"] == {
        "VIRTUAL_ENV": None,
        "UV_NO_PROGRESS": "1",
        "UV_PROJECT": str(paths.CTX.home),
    }


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param(
            ["--index-url", "https://index.example/simple"],
            ["--default-index", "https://index.example/simple"],
            id="separate",
        ),
        pytest.param(
            ["--index-url=https://index.example/simple"],
            ["--default-index=https://index.example/simple"],
            id="attached",
        ),
        pytest.param(
            ["-i", "https://index.example/simple"],
            ["--default-index", "https://index.example/simple"],
            id="short-separate",
        ),
        pytest.param(
            ["-ihttps://index.example/simple"], ["--default-index=https://index.example/simple"], id="short-attached"
        ),
    ],
)
def test_uv_install_passes_index_url_as_default_index(
    pip_args: list[str], expected: list[str], tmp_path: Path, uv_run_subprocess: MagicMock
) -> None:
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    UvBackend().install(
        venv_root=tmp_path, venv_python=venv_python, requirements=["demo"], pip_args=pip_args, verbose=False
    )

    assert uv_run_subprocess.call_args.args[0] == [
        tmp_path / "uv",
        "pip",
        "install",
        "--python",
        str(venv_python),
        "--quiet",
        *expected,
        "demo",
    ]


@pytest.mark.parametrize(
    ("verbose", "args", "flags"),
    [
        # verbose means "do not silence", matching pip; uv's --verbose would print DEBUG logs on every `pipx runpip`
        pytest.param(True, ["show", "demo"], ["demo"], id="verbose-passes-through"),
        pytest.param(True, ["install", "-q", "demo"], ["-q", "demo"], id="verbose-keeps-user-quiet"),
        pytest.param(False, ["show", "-q", "demo"], ["--quiet", "demo"], id="plain-quiet"),
    ],
)
def test_uv_run_raw_pip_verbosity(
    verbose: bool, args: list[str], flags: list[str], tmp_path: Path, uv_run_subprocess: MagicMock
) -> None:
    venv_python: Final[Path] = tmp_path / "bin" / "python"

    UvBackend().run_raw_pip(venv_root=tmp_path, venv_python=venv_python, args=args, verbose=verbose)

    assert uv_run_subprocess.call_args.args[0] == [
        tmp_path / "uv",
        "pip",
        args[0],
        "--python",
        str(venv_python),
        *flags,
    ]


def test_assert_not_pip_under_uv_blocks_pip_on_uv() -> None:
    with pytest.raises(PipxError, match="cannot be installed or exposed via the uv backend"):
        assert_not_pip_under_uv("pip", UV)


@pytest.mark.parametrize(
    ("package_name", "backend_name"),
    [
        pytest.param("pip", PIP, id="allows-pip-on-pip"),
        pytest.param("ruff", UV, id="allows-other-packages-on-uv"),
    ],
)
def test_assert_not_pip_under_uv_allows(package_name: str, backend_name: str) -> None:
    assert_not_pip_under_uv(package_name, backend_name)


def test_uv_list_installed_not_required_uses_distribution_metadata(
    site_packages: Path, tmp_path: Path, uv_run_subprocess: MagicMock
) -> None:
    write_dist_info(site_packages, "root-package")
    write_dist_info(site_packages, "top-package", ["child-package>=1"])
    write_dist_info(site_packages, "child-package")

    installed: Final[set[str]] = UvBackend().list_installed(
        venv_root=tmp_path, venv_python=tmp_path / "bin" / "python", not_required=True
    )

    assert (installed, uv_run_subprocess.called) == ({"root-package", "top-package"}, False)


@pytest.mark.parametrize(
    "run_pip",
    [
        pytest.param(
            lambda _root, python: PipBackend().upgrade_packaging_libraries(python, []),
            id="upgrade-packaging-libraries",
        ),
        pytest.param(
            lambda root, python: PipBackend().install(
                venv_root=root, venv_python=python, requirements=["demo"], pip_args=[], verbose=False
            ),
            id="install",
        ),
        pytest.param(
            lambda root, python: PipBackend().uninstall(
                venv_root=root, venv_python=python, packages=["demo"], verbose=False
            ),
            id="uninstall",
        ),
        pytest.param(
            lambda root, python: PipBackend().list_installed(venv_root=root, venv_python=python, not_required=False),
            id="list-installed",
        ),
        pytest.param(
            lambda root, python: PipBackend().list_outdated(
                venv_root=root, venv_python=python, index_args=[], exclude=[]
            ),
            id="list-outdated",
        ),
        pytest.param(
            lambda root, python: PipBackend().run_raw_pip(
                venv_root=root, venv_python=python, args=["check"], verbose=False
            ),
            id="run-raw-pip",
        ),
    ],
)
def test_pip_backend_starts_pip_without_site_config(
    run_pip: Callable[[Path, Path], set[str] | tuple[OutdatedPackage, ...] | subprocess.CompletedProcess[str] | None],
    tmp_path: Path,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (site_config := tmp_path / ("pip.ini" if WINDOWS else "pip.conf")).write_text(
        "[install]\ntarget = ..\n", encoding="utf-8"
    )
    seen_by_pip: Final[list[bool]] = []

    def record(
        *_args: Sequence[str | Path], **_kwargs: bool | str | dict[str, str | None] | None
    ) -> subprocess.CompletedProcess[str]:
        seen_by_pip.append(site_config.exists())
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")

    mocker.patch("pipx.backends.pip.run_subprocess", autospec=True, side_effect=record)

    run_pip(tmp_path, tmp_path / "bin" / "python")

    assert (seen_by_pip, f"Removing {site_config}" in caplog.text) == ([False], True)


@pytest.fixture
def outdated_process() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout='[{"name":"demo","version":"1","latest_version":"2"}]', stderr=""
    )


def test_pip_backend_list_outdated_forwards_index_settings(
    tmp_path: Path, mocker: MockerFixture, outdated_process: subprocess.CompletedProcess[str]
) -> None:
    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess", autospec=True, return_value=outdated_process
    )

    result: Final = PipBackend().list_outdated(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        index_args=["--index-url", "https://index.example/simple"],
        exclude=["click", "pip"],
    )

    assert (result, run_subprocess.call_args.args[0]) == (
        (OutdatedPackage(name="demo", version="1", latest_version="2"),),
        [
            str(tmp_path / "bin" / "python"),
            "-m",
            "pip",
            "list",
            "--outdated",
            "--format=json",
            "--index-url",
            "https://index.example/simple",
            "--exclude=click",
            "--exclude=pip",
        ],
    )


def test_uv_backend_list_outdated_forwards_index_settings(
    tmp_path: Path, uv_binary: Path, mocker: MockerFixture, outdated_process: subprocess.CompletedProcess[str]
) -> None:
    run_subprocess: Final[MagicMock] = mocker.patch(
        "pipx.backends.uv.run_subprocess", autospec=True, return_value=outdated_process
    )

    result: Final = UvBackend().list_outdated(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        index_args=["--index-url", "https://index.example/simple"],
        exclude=["click", "pip"],
    )

    assert (result, run_subprocess.call_args.args[0]) == (
        (OutdatedPackage(name="demo", version="1", latest_version="2"),),
        [
            uv_binary,
            "pip",
            "list",
            "--python",
            str(tmp_path / "bin" / "python"),
            "--quiet",
            "--outdated",
            "--format=json",
            "--default-index",
            "https://index.example/simple",
            "--exclude=click",
            "--exclude=pip",
        ],
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


@pytest.mark.parametrize(
    ("version_output", "reported"),
    [
        pytest.param("pip 24.0 from /site-packages/pip (python 3.11)\n", "pip 24.0", id="before-lock-support"),
        pytest.param("", "pip of an unknown version", id="unknown"),
    ],
)
def test_pip_backend_install_lock_refuses_pip_without_lock_support(
    version_output: str, reported: str, tmp_path: Path, mocker: MockerFixture
) -> None:
    run: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=version_output, stderr=""),
    )

    with pytest.raises(PipxError) as error:
        PipBackend().install_lock(
            venv_root=tmp_path,
            venv_python=tmp_path / "bin" / "python",
            lock_file=tmp_path / "pylock.toml",
            pip_args=[],
            verbose=False,
        )

    assert (
        f"needs pip>=26.1, but this environment runs {reported}." in " ".join(str(error.value).split()),
        run.call_count,
    ) == (True, 1)


def test_pip_backend_install_lock_passes_lock_to_pip_with_lock_support(tmp_path: Path, mocker: MockerFixture) -> None:
    run: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="pip 26.1 from /pip\n", stderr=""),
    )

    PipBackend().install_lock(
        venv_root=tmp_path,
        venv_python=tmp_path / "bin" / "python",
        lock_file=tmp_path / "pylock.toml",
        pip_args=[],
        verbose=False,
    )

    assert run.call_args.args[0] == [
        str(tmp_path / "bin" / "python"),
        "-m",
        "pip",
        "--no-input",
        "install",
        "--requirement",
        str(tmp_path / "pylock.toml"),
    ]
