from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

_SECTIONS: Final[dict[str, str]] = {
    "bash-completion/completions": "local-completion",
    "zsh/site-functions": "_local-completion",
    "fish/vendor_completions.d": "local-completion.fish",
}


@pytest.fixture
def completion_project(root: Path) -> str:
    return str(root / "testdata/test_package_specifier/local_completion")


@pytest.mark.parametrize("section", list(_SECTIONS), ids=["bash", "zsh", "fish"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_exposes_the_completion_script(
    completion_project: str,
    section: str,
) -> None:
    assert not run_pipx_cli(["install", completion_project])

    exposed: Final[Path] = paths.ctx.completion_dir / section / _SECTIONS[section]
    assert exposed.is_symlink() or exposed.is_file()


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_the_completion_scripts(completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])

    assert not run_pipx_cli(["uninstall", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_unexpose_removes_the_completion_scripts(completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])

    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_restores_the_completion_scripts(completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])
    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not run_pipx_cli(["expose", "local-completion"])

    assert sorted(path.name for path in paths.ctx.completion_dir.rglob("*local-completion*")) == sorted(
        _SECTIONS.values()
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_removes_a_stale_completion_link(completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])
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
