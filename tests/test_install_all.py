from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import PACKAGE_CACHE_DIR_NAME, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("install_all_args", "expected_cooldown"),
    [
        pytest.param([], 7, id="stored"),
        pytest.param(["--cooldown", "0"], 0, id="override"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all(  # ruff:ignore[too-many-positional-arguments]  # pytest injects fixtures by name
    root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    make_pylock: Callable[[str, str], Path],
    install_all_args: list[str],
    expected_cooldown: int,
) -> None:
    find_links: Final[Path] = root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--app", "pycowsay", "--lock", str(lock_file), "pycowsay"])
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["black"]["spec"]])
    assert not run_pipx_cli(["inject", "black", pip_args, "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--json"])
    pipx_list_path: Final[Path] = tmp_path / "pipx_list.json"
    pipx_list_path.write_text(capsys.readouterr().out, encoding="utf-8")

    assert not run_pipx_cli(["uninstall-all"])
    assert not run_pipx_cli(["install-all", *install_all_args, pip_args, str(pipx_list_path)])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])

    installed_names: Final[list[str]] = sorted(json.loads(capsys.readouterr().out)["venvs"])
    black_metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "black")
    pycowsay_metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        installed_names,
        sorted(black_metadata.injected_packages),
        pycowsay_metadata.main_package.expected_apps,
        pycowsay_metadata.main_package.lock_file,
        black_metadata.main_package.cooldown_days,
        black_metadata.injected_packages["pycowsay"].cooldown_days,
    ) == (
        ["black", "pycowsay"],
        ["pycowsay"],
        ["pycowsay"],
        lock_file.resolve(),
        expected_cooldown,
        expected_cooldown,
    )


@pytest.mark.parametrize(
    ("pin_args", "expected_pins"),
    [
        pytest.param([], (True, True), id="all"),
        pytest.param(["--injected-only"], (False, True), id="injected-only"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_restores_pins(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], pin_args: list[str], expected_pins: tuple[bool, bool]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay", *pin_args])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])

    assert not run_pipx_cli(["install-all", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (metadata.main_package.pinned, metadata.injected_packages["black"].pinned) == expected_pins


@pytest.fixture
def recorded_snapshot(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # create an isolated pipx home
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> tuple[Path, Path]:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    snapshot: Final = json.loads(capsys.readouterr().out)
    recorded: Final[Path] = tmp_path / "python-recorded"
    recorded.touch()
    snapshot["venvs"]["pycowsay"]["metadata"]["source_interpreter"] = {
        "__type__": "Path",
        "__Path__": str(recorded),
    }
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(json.dumps(snapshot), encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    return spec_file, recorded


@pytest.mark.parametrize(
    ("python_arg", "use_recorded"),
    [
        pytest.param([], True, id="recorded"),
        pytest.param(["--python", sys.executable], False, id="explicit"),
    ],
)
def test_install_all_selects_interpreter(
    recorded_snapshot: tuple[Path, Path],
    mocker: MockerFixture,
    python_arg: list[str],
    use_recorded: bool,
) -> None:
    spec_file, recorded = recorded_snapshot
    install: Final = mocker.patch("pipx.commands.install.install", autospec=True)
    assert not run_pipx_cli(["install-all", str(spec_file), *python_arg])
    assert Path(install.call_args.args[5]).resolve() == (recorded if use_recorded else Path(sys.executable).resolve())


def test_install_all_reports_missing_recorded_interpreter(
    recorded_snapshot: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    spec_file, recorded = recorded_snapshot
    recorded.unlink()
    assert not run_pipx_cli(["install-all", str(spec_file)])
    printed: Final[str] = " ".join(capsys.readouterr().out.split())
    assert "The exported python interpreter" in printed
    assert "is ignored as not found" in printed


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_force_ignores_explicit_python(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")

    assert not run_pipx_cli(["install-all", str(spec_file), "--force", "--python", sys.executable])
    assert "--python is ignored when --force is passed" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_multiple_errors(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pipx_metadata_path = root / "testdata" / "pipx_metadata_multiple_errors.json"
    assert run_pipx_cli(["install-all", str(pipx_metadata_path)])
    captured = capsys.readouterr()
    assert "The following package(s) failed to install: dotenv, weblate" in captured.err
    assert f"No packages installed after running 'pipx install-all {pipx_metadata_path}'" in captured.out
    if paths.ctx.log_file:
        log_path = paths.ctx.log_file.parent / (paths.ctx.log_file.stem + "_pip_errors.log")
        log_contents = log_path.read_text(encoding="utf-8")
        assert "dotenv" in log_contents
        assert "weblate" in log_contents


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_reports_injected_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    missing_spec: Final[str] = (tmp_path / "missing").as_posix()
    spec_file.write_text(
        capsys.readouterr().out.replace('"package_or_url": "pycowsay"', f'"package_or_url": "{missing_spec}"'),
        encoding="utf-8",
    )
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    expected_error: Final[str] = " ".join(pipx_wrap(f"Unable to parse package spec: {missing_spec}").split())
    assert (result, expected_error in error) == (1, True)


@pytest.mark.parametrize(
    ("install_all_args", "expected_pip_args"),
    [
        pytest.param([], ["--no-cache-dir"], id="recorded"),
        pytest.param(["--pip-args=--no-compile"], ["--no-compile"], id="override"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_restores_recorded_args(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], install_all_args: list[str], expected_pip_args: list[str]
) -> None:
    assert not run_pipx_cli(["install", "--system-site-packages", "--pip-args=--no-cache-dir", "black"])
    assert not run_pipx_cli(["inject", "black", "--pip-args=--no-cache-dir", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])

    assert not run_pipx_cli(["install-all", *install_all_args, str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "black")
    assert (
        metadata.venv_args,
        metadata.main_package.pip_args,
        metadata.injected_packages["pycowsay"].pip_args,
    ) == (["--system-site-packages"], expected_pip_args, expected_pip_args)


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
        pytest.param(None, "Unable to read the spec metadata file {file}: No such file or directory", id="missing"),
        pytest.param(b"\xff", "The spec metadata file {file} is not valid JSON.", id="binary"),
        pytest.param(b"{", "The spec metadata file {file} is not valid JSON.", id="truncated"),
        pytest.param(b"[]", "The spec metadata file {file} is invalid.", id="not-an-object"),
        pytest.param(b'{"venvs": []}', "The spec metadata file {file} is invalid.", id="venvs-not-an-object"),
        pytest.param(b'{"venvs": {}}', "No packages found in the spec metadata file {file}.", id="no-venvs"),
        pytest.param(
            b'{"venvs": {"x": {}}}',
            "Entry 'x' in the spec metadata file {file} is missing 'metadata'.",
            id="no-metadata",
        ),
        pytest.param(
            b'{"venvs": {"x": {"metadata": {"pipx_metadata_version": "0.12"}}}}',
            "Entry 'x' in the spec metadata file {file} is missing 'main_package'.",
            id="no-main-package",
        ),
        pytest.param(
            b'{"venvs": {"x": {"metadata": "x"}}}',
            "Entry 'x' in the spec metadata file {file} is malformed: string indices must be integers, not 'str'",
            id="metadata-not-an-object",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_rejects_bad_spec_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes | None, expected_error: str
) -> None:
    spec_file: Final[Path] = tmp_path / "pipx.json"
    if content is not None:
        spec_file.write_bytes(content)

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    expected: Final[str] = " ".join(pipx_wrap(expected_error.format(file=spec_file)).split())
    assert (result, expected in error) == (1, True)


@pytest.fixture
def spec_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    for spec in ("pycowsay", PKG["pbr"]["spec"], PKG["black"]["spec"]):
        assert not run_pipx_cli(["install", spec])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    return spec_file


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_prints_progress_in_spec_order(
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    spec_file: Path,
) -> None:
    venv_names: Final[list[str]] = list(json.loads(spec_file.read_text(encoding="utf-8"))["venvs"])
    before_venv_subprocess(paths.ctx.venvs / venv_names[0], lambda: time.sleep(0.3))

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert re.findall(r"^installing ([\w-]+)", capsys.readouterr().err, re.MULTILINE) == venv_names


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_installs_entries_before_a_malformed_one(spec_file: Path) -> None:
    spec: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    spec["venvs"] = {"pycowsay": spec["venvs"]["pycowsay"], "malformed": {}}
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    exit_code: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    assert (exit_code, sorted(venv_dir.name for venv_dir in paths.ctx.venvs.iterdir() if venv_dir.is_dir())) == (
        1,
        ["pycowsay"],
    )
