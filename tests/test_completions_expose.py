from __future__ import annotations

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
def test_install_exposes_the_completion_script(
    pipx_temp_env: None,
    completion_project: str,
    section: str,
) -> None:
    assert not run_pipx_cli(["install", completion_project])

    exposed: Final[Path] = paths.ctx.completion_dir / section / _SECTIONS[section]
    assert exposed.is_symlink() or exposed.is_file()


def test_uninstall_removes_the_completion_scripts(pipx_temp_env: None, completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])

    assert not run_pipx_cli(["uninstall", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


def test_unexpose_removes_the_completion_scripts(pipx_temp_env: None, completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])

    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not list(paths.ctx.completion_dir.rglob("*local-completion*"))


def test_expose_restores_the_completion_scripts(pipx_temp_env: None, completion_project: str) -> None:
    assert not run_pipx_cli(["install", completion_project])
    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not run_pipx_cli(["expose", "local-completion"])

    assert sorted(path.name for path in paths.ctx.completion_dir.rglob("*local-completion*")) == sorted(
        _SECTIONS.values()
    )


def test_environment_reports_the_completion_dir(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["environment", "--value", "PIPX_COMPLETION_DIR"])

    assert capsys.readouterr().out.strip() == str(paths.ctx.completion_dir)
