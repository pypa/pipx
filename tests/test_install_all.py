import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import pipx_wrap


@pytest.mark.parametrize(
    ("install_all_args", "expected_cooldown"),
    [
        pytest.param([], 7, id="stored"),
        pytest.param(["--cooldown", "0"], 0, id="override"),
    ],
)
def test_install_all(
    pipx_temp_env: None,
    root: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    make_pylock: Callable[[str, str], Path],
    install_all_args: list[str],
    expected_cooldown: int,
) -> None:
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )
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


def test_install_all_multiple_errors(pipx_temp_env, root, capsys):
    pipx_metadata_path = root / "testdata" / "pipx_metadata_multiple_errors.json"
    assert run_pipx_cli(["install-all", str(pipx_metadata_path)])
    captured = capsys.readouterr()
    assert "The following package(s) failed to install: dotenv, weblate" in captured.err
    assert f"No packages installed after running 'pipx install-all {pipx_metadata_path}'" in captured.out
    if paths.ctx.log_file:
        with open(paths.ctx.log_file.parent / (paths.ctx.log_file.stem + "_pip_errors.log")) as log_fh:
            log_contents = log_fh.read()
            assert "dotenv" in log_contents
            assert "weblate" in log_contents


def test_install_all_reports_injected_failure(
    pipx_temp_env: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    missing: Final[Path] = tmp_path / "missing"
    spec_file.write_text(
        capsys.readouterr().out.replace('"package_or_url": "pycowsay"', f'"package_or_url": "{missing}"'),
        encoding="utf-8",
    )
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    expected_error: Final[str] = " ".join(pipx_wrap(f"Unable to parse package spec: {missing}").split())
    assert (result, expected_error in error) == (1, True)
