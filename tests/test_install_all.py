from __future__ import annotations

import json
import shutil
import sys
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_restores_recorded_interpreter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # ``pipx install-all`` is the migration tool: the snapshot records each environment's
    # ``source_interpreter``, and restoring without ``--python`` should use it, as it did before the
    # dispatch refactor. An explicitly named ``--python`` keeps the last word.
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    snapshot: Final = json.loads(capsys.readouterr().out)

    alt_interpreter: Final[Path] = tmp_path / "python-alt"
    try:
        alt_interpreter.symlink_to(Path(sys.executable))
    except OSError:  # Windows without Developer Mode, matching tests/conftest.py
        shutil.copy2(sys.executable, alt_interpreter)
    assert alt_interpreter != Path(sys.executable).resolve()

    snapshot["venvs"]["pycowsay"]["metadata"]["source_interpreter"] = {
        "__type__": "Path",
        "__Path__": str(alt_interpreter),
    }
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(json.dumps(snapshot), encoding="utf-8")

    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    assert not run_pipx_cli(["install-all", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert metadata.source_interpreter == alt_interpreter


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_reports_missing_recorded_interpreter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    snapshot: Final = json.loads(capsys.readouterr().out)

    gone_interpreter: Final[Path] = tmp_path / "python-gone"
    snapshot["venvs"]["pycowsay"]["metadata"]["source_interpreter"] = {
        "__type__": "Path",
        "__Path__": str(gone_interpreter),
    }
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(json.dumps(snapshot), encoding="utf-8")

    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    assert not run_pipx_cli(["install-all", str(spec_file)])
    captured: Final = capsys.readouterr()

    # pipx_wrap breaks the long path inside the message, so match the sentence around it
    assert "The exported python interpreter" in captured.out
    assert "' is ignored" in captured.out
    assert "as not found" in captured.out


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
