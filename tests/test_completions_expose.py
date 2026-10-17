from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Final

import pytest
from flit_core.wheel import make_wheel_in

from helpers import run_pipx_cli
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_SECTIONS: Final[dict[str, str]] = {
    "bash-completion/completions": "local-completion",
    "zsh/site-functions": "_local-completion",
    "fish/vendor_completions.d": "local-completion.fish",
}


@pytest.fixture
def completion_wheel(local_completion_wheel: Path) -> str:
    return str(local_completion_wheel)


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_selects_completion_only_dependency(
    copy_local_package: Callable[[str], Path],
    make_project_with_dependency: Callable[[str], Path],
    tmp_path: Path,
    backend: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv binary not on PATH")
    project = copy_local_package("local_completion")
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('scripts.local-completion = "local_completion.main:main"\n', ""),
        encoding="utf-8",
    )
    dependency = make_wheel_in(pyproject, tmp_path).file
    parent = make_project_with_dependency(f"local-completion @ {dependency.as_uri()}")
    parent_wheel = make_wheel_in(parent / "pyproject.toml", tmp_path).file

    assert not run_pipx_cli([
        "install",
        str(parent_wheel),
        "--backend",
        backend,
        "--include-resources-from",
        "Local_Completion",
    ])

    metadata = PipxMetadata(paths.ctx.venvs / "empty-project").main_package
    assert metadata.include_resources_from == ["local-completion"]
    assert not metadata.app_paths_of_dependencies
    assert not metadata.man_paths_of_dependencies
    for section, name in _SECTIONS.items():
        exposed = paths.ctx.completion_dir / section / name
        assert exposed.is_file()


@pytest.mark.parametrize("section", list(_SECTIONS), ids=["bash", "zsh", "fish"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_exposes_the_completion_script(
    completion_wheel: str,
    section: str,
) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    exposed: Final[Path] = paths.ctx.completion_dir / section / _SECTIONS[section]
    assert exposed.is_symlink() or exposed.is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    assert not run_pipx_cli(["uninstall", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_unexpose_removes_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_restores_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])
    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not run_pipx_cli(["expose", "local-completion"])

    assert sorted(path.name for path in paths.ctx.completion_dir.rglob("*local-completion*")) == sorted(
        _SECTIONS.values()
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_removes_a_stale_completion_link(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])
    section: Final[str] = "bash-completion/completions"
    source: Final[Path] = paths.ctx.venvs / "local-completion" / "share" / "bash-completion" / "completions" / "orphan"
    source.write_text("# orphan completion\n", encoding="utf-8")
    orphan: Final[Path] = paths.ctx.completion_dir / section / "orphan"
    orphan.symlink_to(source)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "local-completion"])

    assert not orphan.exists()


@pytest.mark.usefixtures("pipx_temp_env")
def test_environment_reports_the_completion_dir(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["environment", "--value", "PIPX_COMPLETION_DIR"])

    assert capsys.readouterr().out.strip() == str(paths.ctx.completion_dir)
