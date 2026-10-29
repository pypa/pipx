from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, run_pipx_cli
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("scope_args", "pip_command"),
    [
        pytest.param([], "list", id="list"),
        pytest.param([], "list --format=freeze", id="splits-single-argument"),
        pytest.param(["--global"], "list", id="global", marks=SKIP_IF_WINDOWS),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip(scope_args: list[str], pip_command: str) -> None:
    assert not run_pipx_cli(["install", *scope_args, "pycowsay"])
    assert not run_pipx_cli(["runpip", *scope_args, "pycowsay", pip_command])


@pytest.mark.parametrize(
    ("backend", "option_args"),
    [
        pytest.param("pip", (), id="pip-no-option"),
        pytest.param("pip", ("--only-binary", "empty-project"), id="pip-only-binary"),
        pytest.param("pip", ("--no-binary", "empty-project"), id="pip-no-binary"),
        pytest.param("pip", ("--proxy", "empty-project"), id="pip-proxy"),
        pytest.param("pip", ("--only-bin", "empty-project"), id="pip-only-binary-abbreviated"),
        pytest.param("pip", ("--pre",), id="pip-pre-flag-prefixes-prefix"),
        pytest.param("pip", ("--no-build-iso",), id="pip-no-build-isolation-abbreviated"),
        pytest.param("uv", ("-P", "empty-project"), id="uv-upgrade-package"),
        pytest.param("uv", ("--refresh",), id="uv-refresh-flag-prefixes-refresh-package"),
        pytest.param("uv", ("--no-sources",), id="uv-no-sources-flag-prefixes-no-sources-package"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_refreshes_main_package_metadata(
    empty_project: Path, empty_project_wheel: Path, backend: str, option_args: tuple[str, ...]
) -> None:
    assert not run_pipx_cli(["install", "--backend", backend, "--editable", str(empty_project)])

    metadata_path: Final[Path] = paths.CTX.venvs / "empty-project" / "pipx_metadata.json"
    before: Final = json.loads(metadata_path.read_text())["main_package"]
    assert (before["package_or_url"], before["pip_args"]) == (str(empty_project.resolve()), ["--editable"])

    assert not run_pipx_cli([
        "runpip",
        "empty-project",
        "install",
        "--force-reinstall",
        *option_args,
        str(empty_project_wheel),
    ])

    after: Final = json.loads(metadata_path.read_text())["main_package"]
    assert (after["package_or_url"], after["pip_args"]) == (str(empty_project_wheel.resolve()), [])


@pytest.mark.parametrize(
    "editable_args",
    [
        pytest.param(("--edit", "{project}"), id="abbreviated"),
        pytest.param(("--edit={project}",), id="abbreviated-attached"),
        pytest.param(("--editable={project}",), id="attached"),
        pytest.param(("-qe", "{project}"), id="clustered"),
        pytest.param(("-e{project}",), id="short-attached"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_records_editable_spelling(
    empty_project: Path, empty_project_wheel: Path, editable_args: tuple[str, ...]
) -> None:
    assert not run_pipx_cli(["install", str(empty_project_wheel)])

    assert not run_pipx_cli([
        "runpip",
        "empty-project",
        "install",
        *(arg.format(project=empty_project) for arg in editable_args),
    ])

    main_package: Final = PipxMetadata(paths.CTX.venvs / "empty-project").main_package
    assert (main_package.package_or_url, main_package.pip_args) == (str(empty_project.resolve()), ["--editable"])


_NEW_INDEX: Final[tuple[str, ...]] = ("--no-index", "--find-links", "{new}")


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.parametrize(
    ("install_args", "runpip_args", "expected"),
    [
        pytest.param((), (*_NEW_INDEX, "empty-project"), _NEW_INDEX, id="record"),
        pytest.param(("--pip-args=--find-links {old}",), (*_NEW_INDEX, "empty-project"), _NEW_INDEX, id="replace"),
        pytest.param(("--pip-args=--find-links {old}",), ("{wheel}",), ("--find-links", "{old}"), id="keep"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_records_index_options(
    empty_project: Path,
    empty_project_wheel: Path,
    *,
    backend: str,
    install_args: tuple[str, ...],
    runpip_args: tuple[str, ...],
    expected: tuple[str, ...],
) -> None:
    links: Final[dict[str, str]] = {
        "old": str(empty_project.parent),
        "new": str(empty_project_wheel.parent),
        "wheel": str(empty_project_wheel),
    }

    def fill(args: tuple[str, ...]) -> list[str]:
        return [arg.format_map(links) for arg in args]

    assert not run_pipx_cli(["install", "--backend", backend, *fill(install_args), "--editable", str(empty_project)])

    assert not run_pipx_cli(["runpip", "empty-project", "install", "--force-reinstall", *fill(runpip_args)])

    assert PipxMetadata(paths.CTX.venvs / "empty-project").main_package.pip_args == fill(expected)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param("uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_resolves_relative_paths_in_working_directory(
    empty_project_wheel: Path, local_extras_wheel: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    assert not run_pipx_cli(["install", "--backend", backend, str(empty_project_wheel)])
    # a wheel's data files unpack into the venv root, so a file there must not stand in for the user's
    (paths.CTX.venvs / "empty-project" / "requirements.txt").write_text("picked-by-an-installed-wheel\n")
    (tmp_path / "requirements.txt").write_text(f"{local_extras_wheel}\n")
    monkeypatch.chdir(tmp_path)

    assert not run_pipx_cli(["runpip", "empty-project", "install", "-r", "requirements.txt"])

    assert "repeatme" in Venv(paths.CTX.venvs / "empty-project").list_installed_packages()


@pytest.mark.parametrize(
    "find_links_args",
    [
        pytest.param(("-f", "wheels"), id="short"),
        pytest.param(("-fwheels",), id="short-attached"),
        pytest.param(("--find-links", "./wheels"), id="long"),
        pytest.param(("--find-links=wheels",), id="long-attached"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_relative_find_links_survive_reinstall(
    empty_project_wheel: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, find_links_args: tuple[str, ...]
) -> None:
    assert not run_pipx_cli(["install", str(empty_project_wheel)])
    (wheels := tmp_path / "wheels").mkdir()
    shutil.copy2(empty_project_wheel, wheels)
    monkeypatch.chdir(tmp_path)
    assert not run_pipx_cli(["runpip", "empty-project", "install", "--no-index", *find_links_args, "empty-project"])
    monkeypatch.chdir(paths.CTX.home)

    assert not run_pipx_cli(["reinstall", "empty-project"])
