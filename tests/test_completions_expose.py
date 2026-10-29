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


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param(
            "uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_selects_completion_only_dependency(
    copy_local_package: Callable[[str], Path],
    make_project_with_dependency: Callable[[str], Path],
    tmp_path: Path,
    backend: str,
) -> None:
    pyproject: Final[Path] = copy_local_package("local_completion") / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('scripts.local-completion = "local_completion.main:main"\n', ""),
        encoding="utf-8",
    )
    dependency: Final[Path] = make_wheel_in(pyproject, tmp_path).file
    parent: Final[Path] = make_project_with_dependency(f"local-completion @ {dependency.as_uri()}")

    assert not run_pipx_cli([
        "install",
        str(make_wheel_in(parent / "pyproject.toml", tmp_path).file),
        "--backend",
        backend,
        "--include-resources-from",
        "Local_Completion",
    ])

    metadata: Final = PipxMetadata(paths.CTX.venvs / "empty-project").main_package
    assert (
        metadata.include_resources_from,
        bool(metadata.app_paths_of_dependencies),
        bool(metadata.man_paths_of_dependencies),
        [(paths.CTX.completion_dir / section / name).is_file() for section, name in _SECTIONS.items()],
    ) == (["local-completion"], False, False, [True] * len(_SECTIONS))


@pytest.mark.parametrize("section", list(_SECTIONS), ids=["bash", "zsh", "fish"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_exposes_the_completion_script(
    completion_wheel: str,
    section: str,
) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    exposed: Final[Path] = paths.CTX.completion_dir / section / _SECTIONS[section]
    assert exposed.is_symlink() or exposed.is_file()


@pytest.fixture
def completion_wheel(local_completion_wheel: Path) -> str:
    return str(local_completion_wheel)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    assert not run_pipx_cli(["uninstall", "local-completion"])

    assert not list(paths.CTX.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_unexpose_removes_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])

    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not list(paths.CTX.completion_dir.rglob("*local-completion*"))


@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_restores_the_completion_scripts(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])
    assert not run_pipx_cli(["unexpose", "local-completion"])

    assert not run_pipx_cli(["expose", "local-completion"])

    assert sorted(path.name for path in paths.CTX.completion_dir.rglob("*local-completion*")) == sorted(
        _SECTIONS.values()
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_removes_a_stale_completion_link(completion_wheel: str) -> None:
    assert not run_pipx_cli(["install", completion_wheel])
    source: Final[Path] = paths.CTX.venvs / "local-completion" / "share" / "bash-completion" / "completions" / "orphan"
    source.write_text("# orphan completion\n", encoding="utf-8")
    (orphan := paths.CTX.completion_dir / "bash-completion" / "completions" / "orphan").symlink_to(source)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "local-completion"])

    assert not orphan.exists()


@pytest.mark.usefixtures("pipx_temp_env")
def test_environment_reports_the_completion_dir(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["environment", "--value", "PIPX_COMPLETION_DIR"])

    assert capsys.readouterr().out.strip() == str(paths.CTX.completion_dir)
