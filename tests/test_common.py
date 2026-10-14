from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands import common
from pipx.commands.common import (
    add_suffix,
    expose_resources_globally,
    get_exposed_paths_for_package,
    package_name_from_spec,
    remove_stale_venv_resources,
    reuse_resource_dir_scans,
)
from pipx.constants import MACOS
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pytest_mock import MockerFixture


@skip_if_windows
def test_get_exposed_paths_ignores_recursive_symlink(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    loop = local_resource_dir / "recursiveexample"
    loop.symlink_to(loop.name)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert loop not in exposed


@skip_if_windows
def test_expose_app_scripts_ignores_pythonpath(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    shadow_path = tmp_path / "shadow"
    shadow_path.mkdir()

    app_path = venv_resource_path / "demo"
    app_path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"if {str(shadow_path)!r} in sys.path:\n"
        "    raise SystemExit('PYTHONPATH leaked into app script')\n"
        "print('ok')\n"
    )
    app_path.chmod(0o755)

    expose_resources_globally("app", local_resource_dir, [app_path], force=False)

    assert app_path.read_text().splitlines()[0] == f"#!{sys.executable} -E"

    result = subprocess.run(
        [app_path],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(shadow_path)},
        text=True,
    )
    assert result.stdout == "ok\n"


@skip_if_windows
@pytest.mark.parametrize(
    ("overflow", "separator", "flag"),
    [
        pytest.param(0, b"\n", b" -E", id="flag-fits"),
        pytest.param(1, b"\n", b"", id="flag-one-byte-over"),
        pytest.param(0, b"", b" -E", id="flag-fits-without-newline"),
    ],
)
def test_expose_app_scripts_keep_shebang_within_kernel_limit(
    tmp_path: Path, overflow: int, separator: bytes, flag: bytes
) -> None:
    max_shebang_length: Final[int] = 512 if MACOS else 127
    shebang = b"#!/" + b"x" * (max_shebang_length + overflow - len(b"#!/python -E") - len(separator)) + b"python"
    (app_path := tmp_path / "demo").write_bytes(shebang + separator)

    expose_resources_globally("app", tmp_path / "bin", [app_path], force=False)

    assert app_path.read_bytes() == shebang + flag + separator


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_remove_stale_venv_resources_keeps_files_pipx_does_not_own(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    venv = Venv(paths.ctx.venvs / "pycowsay")
    bin_dir = paths.ctx.bin_dir

    owned = bin_dir / "stale-owned"
    owned.symlink_to(venv.pipx_metadata.main_package.app_paths[0])
    replaced = bin_dir / "stale-replaced"
    replaced.write_text("belongs to the user")

    remove_stale_venv_resources({owned, replaced}, venv, bin_dir, paths.ctx.man_dir)

    assert (owned.exists(), replaced.read_text()) == (False, "belongs to the user")


# A binary pipx did not create is parsed as if it were a launcher, so the bytes trailing a stray "#!" reach
# os.fsdecode and stat as an interpreter path. Windows rejects the undecodable one, every platform the NUL.
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"MZ\x90\x00\x03#!\xff\xfe\x80\x81 more binary\n", id="undecodable-interpreter"),
        pytest.param(b"MZ\x90\x00\x03#!/opt/no\x00pe/bin/python\n", id="nul-in-interpreter"),
    ],
)
def test_get_exposed_paths_ignores_foreign_binary(tmp_path: Path, mocker: MockerFixture, payload: bytes) -> None:
    # Only copy-based environments read a shebang to establish ownership, so without this the symlink branch
    # short-circuits the scan and the parse under test never runs off Windows.
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    foreign = local_resource_dir / "foreign.exe"
    foreign.write_bytes(payload)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert foreign not in exposed


@pytest.mark.parametrize(
    "owned",
    [pytest.param(True, id="shebang-into-venv"), pytest.param(False, id="shebang-elsewhere")],
)
def test_get_exposed_paths_matches_copied_launcher(tmp_path: Path, mocker: MockerFixture, owned: bool) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    elsewhere = tmp_path / "other"
    elsewhere.mkdir()
    launcher = local_resource_dir / "myapp"
    launcher.write_text(f"#!{(venv_resource_path if owned else elsewhere) / 'python'}\n")

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert (launcher in exposed) is owned


@skip_if_windows
def test_get_exposed_paths_matches_venv_reached_through_symlinked_dir(tmp_path: Path) -> None:
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (alias := tmp_path / "alias").symlink_to(venv_resource_path)
    (local_resource_dir := tmp_path / "bin").mkdir()
    (exposed_app := local_resource_dir / "myapp").symlink_to(venv_resource_path / "myapp")

    assert get_exposed_paths_for_package(alias, local_resource_dir) == {exposed_app}


@skip_if_windows
def test_get_exposed_paths_ignores_symlink_into_removed_dir(tmp_path: Path) -> None:
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (local_resource_dir / "myapp").symlink_to(tmp_path / "removed" / "myapp")

    assert get_exposed_paths_for_package(venv_resource_path, local_resource_dir) == set()


def test_get_exposed_paths_matches_copied_launcher_with_quoted_interpreter(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (launcher := local_resource_dir / "myapp").write_text(f'#!"{venv_resource_path / "python"}" -E\n')

    assert get_exposed_paths_for_package(venv_resource_path, local_resource_dir) == {launcher}


def test_get_exposed_paths_ignores_unreadable_copy(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (local_resource_dir / "myapp").mkdir()

    assert get_exposed_paths_for_package(venv_resource_path, local_resource_dir) == set()


def test_get_exposed_paths_matches_copy_by_recorded_source(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (source := tmp_path / "source" / "myapp.1").parent.mkdir()
    source.write_text("page")
    (local_resource_dir := tmp_path / "man1").mkdir()
    (copy := local_resource_dir / "myapp.1").write_text("page")

    exposed = get_exposed_paths_for_package(tmp_path / "missing", local_resource_dir, {"myapp.1": [source]})

    assert exposed == {copy}


def test_reuse_resource_dir_scans_skips_copy_removed_after_scan(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv_man1").mkdir()
    (venv_resource_path / "myapp.1").write_text("page")
    (local_resource_dir := tmp_path / "man1").mkdir()
    (copy := local_resource_dir / "myapp.1").write_text("page")

    with reuse_resource_dir_scans():
        get_exposed_paths_for_package(tmp_path / "other_venv_man1", local_resource_dir)
        copy.unlink()
        exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert exposed == set()


@pytest.mark.parametrize(
    ("name", "windows", "expected"),
    [
        pytest.param("pycowsay", False, "pycowsay@1", id="posix-plain"),
        pytest.param("pip3.14", False, "pip3.14@1", id="posix-dotted"),
        pytest.param("tool.exe", False, "tool.exe@1", id="posix-exe-is-part-of-name"),
        pytest.param("pip3.14.exe", True, "pip3.14@1.exe", id="windows-exe"),
        pytest.param("tool.CMD", True, "tool@1.CMD", id="windows-cmd-any-case"),
        pytest.param("pip3.14", True, "pip3.14@1", id="windows-dotted-without-extension"),
    ],
)
def test_add_suffix(mocker: MockerFixture, name: str, windows: bool, expected: str) -> None:
    mocker.patch.object(common, "WINDOWS", windows)
    assert add_suffix(name, "@1") == expected


@pytest.mark.parametrize(
    ("backend", "env_backend", "extras", "expected"),
    [
        pytest.param("pip", None, "", "Foo_Bar.X", id="pip-keeps-declared-name"),
        pytest.param("pip", None, "[extra]", "Foo_Bar.X", id="pip-with-extras"),
        pytest.param("uv", None, "[extra]", "foo-bar-x", id="uv-normalizes-name"),
        pytest.param(None, "uv", "", "foo-bar-x", id="uv-from-environment"),
    ],
)
def test_package_name_from_spec_reads_static_name_without_building(
    tmp_path: Path, backend: str | None, env_backend: str | None, extras: str, expected: str
) -> None:
    # the build backend does not exist, so any attempt to build the project would fail
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["no-such-build-backend"]\nbuild-backend = "no_such_build_backend"\n'
        '[project]\nname = "Foo_Bar.X"\n',
        encoding="utf-8",
    )

    assert (
        package_name_from_spec(
            f"{tmp_path}{extras}", sys.executable, pip_args=[], verbose=False, backend=backend, env_backend=env_backend
        )
        == expected
    )


@pytest.mark.parametrize(
    ("backend", "env_backend", "extras", "expected"),
    [
        pytest.param("pip", None, "", "Foo_Bar.X", id="pip-keeps-declared-name"),
        pytest.param("pip", None, "[extra]", "Foo_Bar.X", id="pip-with-extras"),
        pytest.param("uv", None, "[extra]", "foo-bar-x", id="uv-normalizes-name"),
        pytest.param(None, "uv", "", "foo-bar-x", id="uv-from-environment"),
    ],
)
def test_package_name_from_spec_reads_wheel_metadata_without_installing(
    make_wheel: Callable[[dict[str, str]], Path],
    backend: str | None,
    env_backend: str | None,
    extras: str,
    expected: str,
) -> None:
    # without a WHEEL file no installer accepts the archive, so installing it to learn the name would fail
    wheel: Final[Path] = make_wheel({"foo_bar_x-1.dist-info/METADATA": "Name: Foo_Bar.X\n"})

    assert (
        package_name_from_spec(
            f"{wheel}{extras}", sys.executable, pip_args=[], verbose=False, backend=backend, env_backend=env_backend
        )
        == expected
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_name_from_spec_builds_setup_py_project(local_extras_project: Path) -> None:
    assert package_name_from_spec(f"{local_extras_project}[cow]", sys.executable, pip_args=[], verbose=False) == (
        "repeatme"
    )
