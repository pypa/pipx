from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, run_pipx_cli
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
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import MagicMock

    from _pytest.mark.structures import ParameterSet
    from pytest_mock import MockerFixture


@SKIP_IF_WINDOWS
def test_get_exposed_paths_ignores_recursive_symlink(tmp_path: Path) -> None:
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (loop := local_resource_dir / "recursiveexample").symlink_to("recursiveexample")

    assert loop not in get_exposed_paths_for_package(venv_resource_path, local_resource_dir)


@SKIP_IF_WINDOWS
def test_expose_app_scripts_ignores_pythonpath(tmp_path: Path) -> None:
    (shadow_path := tmp_path / "shadow").mkdir()
    (app_path := tmp_path / "venv_bin" / "demo").parent.mkdir()
    app_path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"if {str(shadow_path)!r} in sys.path:\n"
        "    raise SystemExit('PYTHONPATH leaked into app script')\n"
        "print('ok')\n"
    )
    app_path.chmod(0o755)

    expose_resources_globally("app", tmp_path / "bin", [app_path], force=False)

    result: Final = subprocess.run(
        [app_path],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(shadow_path)},
        text=True,
    )
    assert (app_path.read_text().splitlines()[0], result.stdout) == (f"#!{sys.executable} -E", "ok\n")


@SKIP_IF_WINDOWS
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
    shebang: Final[bytes] = (
        b"#!/" + b"x" * ((512 if MACOS else 127) + overflow - len(b"#!/python -E") - len(separator)) + b"python"
    )
    (app_path := tmp_path / "demo").write_bytes(shebang + separator)

    expose_resources_globally("app", tmp_path / "bin", [app_path], force=False)

    assert app_path.read_bytes() == shebang + flag + separator


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "link", [pytest.param(Path.hardlink_to, id="hard-link"), pytest.param(Path.symlink_to, id="symlink")]
)
def test_expose_app_scripts_leave_installer_cache_intact(tmp_path: Path, link: Callable[[Path, Path], None]) -> None:
    (cached_path := tmp_path / "cache" / "demo").parent.mkdir()
    cached_path.write_bytes(b"#!/usr/bin/python3\n")
    (app_path := tmp_path / "venv_bin" / "demo").parent.mkdir()
    link(app_path, cached_path)

    expose_resources_globally("app", tmp_path / "bin", [app_path], force=False)

    assert (cached_path.read_bytes(), app_path.read_bytes()) == (b"#!/usr/bin/python3\n", b"#!/usr/bin/python3 -E\n")


@SKIP_IF_WINDOWS
def test_expose_app_scripts_keep_mode_on_shebang_rewrite(tmp_path: Path) -> None:
    (app_path := tmp_path / "demo").write_bytes(b"#!/usr/bin/python3\n")
    app_path.chmod(0o750)

    expose_resources_globally("app", tmp_path / "bin", [app_path], force=False)

    assert (app_path.read_bytes(), app_path.stat().st_mode & 0o777) == (b"#!/usr/bin/python3 -E\n", 0o750)


@pytest.mark.parametrize(
    ("resource_type", "resource", "suffix"),
    [
        pytest.param("app", "bin/..", "", id="app-parent-directory"),
        pytest.param("man", "share/man/man1/..", "", id="man-parent-directory"),
        pytest.param("app", "bin/demo", "/../../state/demo", id="suffix-with-separator"),
    ],
)
def test_expose_refuses_name_leading_out_of_resource_dir(
    tmp_path: Path, resource_type: str, resource: str, suffix: str
) -> None:
    (resource_path := tmp_path / "venv" / resource).parent.mkdir(parents=True)
    (local_resource_dir := tmp_path / "local" / "resources").mkdir(parents=True)
    (unrelated := tmp_path / "local" / "state" / "history").parent.mkdir()
    unrelated.touch()

    with pytest.raises(PipxError, match=r"^Refusing to expose"):
        expose_resources_globally(resource_type, local_resource_dir, [resource_path], force=True, suffix=suffix)

    assert (unrelated.exists(), list(local_resource_dir.iterdir()), (unrelated.parent / "demo").exists()) == (
        True,
        [],
        False,
    )


@pytest.mark.parametrize(
    ("resource", "suffix", "module"),
    [
        pytest.param("bin/enum.py", "", "enum", id="source-module"),
        pytest.param("bin/re.pyc", "", "re", id="bytecode-module"),
        pytest.param("bin/collections/__init__.py", "", "collections", id="package-directory"),
        pytest.param("bin/re", ".py", "re", id="suffix-makes-module"),
        pytest.param("bin/pipx.py", "", "pipx", id="pipx-module"),
        pytest.param("bin/pipx/__init__.py", "", "pipx", id="pipx-package"),
    ],
)
def test_expose_refuses_app_named_like_shadowed_module(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, resource: str, suffix: str, module: str
) -> None:
    (resource_path := tmp_path / "venv" / resource).parent.mkdir(parents=True)
    resource_path.write_text("")
    (tmp_path / "local").mkdir()
    app_path: Final[Path] = tmp_path / "venv" / "bin" / Path(resource).relative_to("bin").parts[0]

    expose_resources_globally("app", tmp_path / "local", [app_path], force=False, suffix=suffix)

    assert (list((tmp_path / "local").iterdir()), f"in place of the {module} module." in caplog.text) == ([], True)


@pytest.mark.parametrize(
    ("resource_type", "resource", "source", "exposed"),
    [
        pytest.param("app", "bin/enum", "bin/enum", "enum", id="app-without-module-suffix"),
        pytest.param("app", "bin/enum_tool.py", "bin/enum_tool.py", "enum_tool.py", id="app-not-a-stdlib-module"),
        pytest.param("app", "bin/tools/__init__.py", "bin/tools", "tools", id="directory-not-a-stdlib-module"),
        pytest.param("man", "share/man/man1/re.py", "share/man/man1/re.py", "man1/re.py", id="man-page"),
    ],
)
def test_expose_keeps_names_that_shadow_no_stdlib_module(
    tmp_path: Path, resource_type: str, resource: str, source: str, exposed: str
) -> None:
    (resource_path := tmp_path / "venv" / resource).parent.mkdir(parents=True)
    resource_path.write_text("")

    expose_resources_globally(resource_type, tmp_path / "local", [tmp_path / "venv" / source], force=False)

    assert (tmp_path / "local" / exposed).exists()


@SKIP_IF_WINDOWS
def test_expose_force_keeps_directory_in_place_of_app(tmp_path: Path) -> None:
    (app_path := tmp_path / "venv" / "demo").parent.mkdir()
    app_path.write_text("#!/bin/sh\n")
    (kept := tmp_path / "bin" / "demo" / "keep").parent.mkdir(parents=True)
    kept.touch()

    assert (expose_resources_globally("app", tmp_path / "bin", [app_path], force=True), kept.exists()) == (
        [kept.parent],
        True,
    )


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    ("resource_type", "resource", "exposed"),
    [
        pytest.param("app", "bin/tool", "tool", id="app"),
        pytest.param("man", "share/man/man1/tool.1", "man1/tool.1", id="man"),
        pytest.param(
            "completion", "share/bash-completion/completions/tool", "bash-completion/completions/tool", id="completion"
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_keeps_link_to_resource_another_venv_is_replacing(
    tmp_path: Path, resource_type: str, resource: str, exposed: str
) -> None:
    (paths.CTX.venvs / "holder").mkdir(parents=True)
    (path := paths.CTX.venvs / "other" / resource).parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / exposed).parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(held := paths.CTX.venvs / "holder" / resource)

    assert (expose_resources_globally(resource_type, tmp_path, [path], force=False), link.readlink()) == ([link], held)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_force_replaces_link_to_resource_another_venv_is_replacing(tmp_path: Path) -> None:
    (paths.CTX.venvs / "holder").mkdir(parents=True)
    (path := paths.CTX.venvs / "other" / "bin" / "tool").parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / "tool").symlink_to(paths.CTX.venvs / "holder" / "bin" / "tool")

    assert (expose_resources_globally("app", tmp_path, [path], force=True), link.readlink()) == ([], path)


_HELD_RESOURCES: Final[list[ParameterSet]] = [
    pytest.param("app", "bin/tool", "tool", "app_paths", id="app"),
    pytest.param("man", "share/man/man1/tool.1", "man1/tool.1", "man_paths", id="man"),
    pytest.param(
        "completion",
        "share/bash-completion/completions/tool",
        "bash-completion/completions/tool",
        "completion_paths",
        id="completion",
    ),
]


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(("resource_type", "resource", "exposed", "field"), _HELD_RESOURCES)
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_keeps_link_to_resource_its_venv_still_records(
    tmp_path: Path, resource_type: str, resource: str, exposed: str, field: str
) -> None:
    (held := paths.CTX.venvs / "holder" / resource).parent.mkdir(parents=True)
    _write_holder_metadata({field: [held]})
    (path := paths.CTX.venvs / "other" / resource).parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / exposed).parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(held)

    assert (expose_resources_globally(resource_type, tmp_path, [path], force=False), link.readlink()) == ([link], held)


def _write_holder_metadata(recorded: dict[str, list[Path]], *, injected: bool = False) -> None:
    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "holder", read=False)
    main_package: Final = replace(metadata.main_package, package="holder", package_or_url="holder")
    if injected:
        metadata.main_package = main_package
        metadata.injected_packages = {"extra": replace(main_package, package="extra", **recorded)}
    else:
        metadata.main_package = replace(main_package, **recorded)
    metadata.write()


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_keeps_link_to_app_an_injected_package_still_records(tmp_path: Path) -> None:
    (held := paths.CTX.venvs / "holder" / "bin" / "tool").parent.mkdir(parents=True)
    _write_holder_metadata({"app_paths": [held]}, injected=True)
    (path := paths.CTX.venvs / "other" / "bin" / "tool").parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / "tool").symlink_to(held)

    assert (expose_resources_globally("app", tmp_path, [path], force=False), link.readlink()) == ([link], held)


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(("resource_type", "resource", "exposed", "field"), _HELD_RESOURCES)
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_replaces_link_to_resource_its_venv_dropped(
    tmp_path: Path, resource_type: str, resource: str, exposed: str, field: str
) -> None:
    (paths.CTX.venvs / "holder" / "bin").mkdir(parents=True)
    _write_holder_metadata({field: [paths.CTX.venvs / "holder" / "bin" / "holder"]})
    (path := paths.CTX.venvs / "other" / resource).parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / exposed).parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(paths.CTX.venvs / "holder" / resource)

    assert (expose_resources_globally(resource_type, tmp_path, [path], force=False), link.readlink()) == ([], path)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_warns_that_held_link_target_is_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (paths.CTX.venvs / "holder").mkdir(parents=True)
    (path := paths.CTX.venvs / "other" / "bin" / "tool").parent.mkdir(parents=True)
    path.touch()
    (tmp_path / "tool").symlink_to(paths.CTX.venvs / "holder" / "bin" / "tool")

    expose_resources_globally("app", tmp_path, [path], force=False)

    assert "which is missing" in " ".join(caplog.text.split())


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "target",
    [
        pytest.param("venvs/removed/bin/tool", id="removed-venv"),
        pytest.param("venvs/other/bin/renamed", id="own-venv"),
        pytest.param("venvs/removed", id="venv-dir"),
        pytest.param("trash/tool", id="outside-venvs"),
        pytest.param("../../tool", id="loop"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_expose_replaces_left_over_link(tmp_path: Path, target: str) -> None:
    (path := paths.CTX.venvs / "other" / "bin" / "tool").parent.mkdir(parents=True)
    path.touch()
    (link := tmp_path / "tool").symlink_to(paths.CTX.venvs.parent / target)

    assert (expose_resources_globally("app", tmp_path, [path], force=False), link.readlink()) == ([], path)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_remove_stale_venv_resources_keeps_files_pipx_does_not_own(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    venv: Final[Venv] = Venv(paths.CTX.venvs / "pycowsay")
    (owned := paths.CTX.bin_dir / "stale-owned").symlink_to(venv.pipx_metadata.main_package.app_paths[0])
    (replaced := paths.CTX.bin_dir / "stale-replaced").write_text("belongs to the user")

    remove_stale_venv_resources({owned, replaced}, venv, paths.CTX.bin_dir, paths.CTX.man_dir)

    assert (owned.exists(), replaced.read_text()) == (False, "belongs to the user")


# pipx parses a binary it did not create as if it were a launcher, so the bytes trailing a stray "#!" reach
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
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (foreign := local_resource_dir / "foreign.exe").write_bytes(payload)

    assert foreign not in get_exposed_paths_for_package(venv_resource_path, local_resource_dir)


@pytest.mark.parametrize(
    "owned",
    [pytest.param(True, id="shebang-into-venv"), pytest.param(False, id="shebang-elsewhere")],
)
def test_get_exposed_paths_matches_copied_launcher(tmp_path: Path, mocker: MockerFixture, owned: bool) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (elsewhere := tmp_path / "other").mkdir()
    (launcher := local_resource_dir / "myapp").write_text(
        f"#!{(venv_resource_path if owned else elsewhere) / 'python'}\n"
    )

    assert (launcher in get_exposed_paths_for_package(venv_resource_path, local_resource_dir)) is owned


@SKIP_IF_WINDOWS
def test_get_exposed_paths_matches_venv_reached_through_symlinked_dir(tmp_path: Path) -> None:
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (alias := tmp_path / "alias").symlink_to(venv_resource_path)
    (local_resource_dir := tmp_path / "bin").mkdir()
    (exposed_app := local_resource_dir / "myapp").symlink_to(venv_resource_path / "myapp")

    assert get_exposed_paths_for_package(alias, local_resource_dir) == {exposed_app}


@SKIP_IF_WINDOWS
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


# off Windows, pip and uv start a launcher this way when the interpreter path is too long for a shebang or holds a space
@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    ("exec_line", "owned"),
    [
        pytest.param("'''exec' {python} \"$0\" \"$@\"", True, id="pip-unquoted"),
        pytest.param('\'\'\'exec\' "{python}" "$0" "$@"', True, id="pip-double-quoted"),
        pytest.param("'''exec' '{python}' \"$0\" \"$@\"", True, id="uv-single-quoted"),
        pytest.param("'''exec' '{python}", False, id="unbalanced-quote"),
        pytest.param("'''exec' ", False, id="no-interpreter"),
    ],
)
def test_get_exposed_paths_matches_copied_launcher_with_sh_trampoline(
    tmp_path: Path, mocker: MockerFixture, exec_line: str, owned: bool
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv_bin").mkdir()
    (local_resource_dir := tmp_path / "bin").mkdir()
    (launcher := local_resource_dir / "myapp").write_text(
        f"#!/bin/sh\n{exec_line.format(python=venv_resource_path / 'python')}\n' '''\n"
    )

    assert (launcher in get_exposed_paths_for_package(venv_resource_path, local_resource_dir)) is owned


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

    assert get_exposed_paths_for_package(tmp_path / "missing", local_resource_dir, {"myapp.1": [source]}) == {copy}


def test_reuse_resource_dir_scans_skips_copy_removed_after_scan(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    (venv_resource_path := tmp_path / "venv_man1").mkdir()
    (venv_resource_path / "myapp.1").write_text("page")
    (local_resource_dir := tmp_path / "man1").mkdir()
    (copy := local_resource_dir / "myapp.1").write_text("page")

    with reuse_resource_dir_scans():
        get_exposed_paths_for_package(tmp_path / "other_venv_man1", local_resource_dir)
        copy.unlink()
        exposed: Final[set[Path]] = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

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
        pytest.param("hello.py", True, "hello@1.py", id="windows-script-extension"),
        pytest.param("hello.ps1", True, "hello@1.ps1", id="windows-extension-outside-pathext"),
        pytest.param("hello.py", False, "hello.py@1", id="posix-script-extension"),
    ],
)
def test_add_suffix(mocker: MockerFixture, name: str, windows: bool, expected: str) -> None:
    mocker.patch.object(common, "WINDOWS", windows)
    assert add_suffix(name, "@1") == expected


_NAME_BY_BACKEND: Final[list[ParameterSet]] = [
    pytest.param("pip", None, "", "Foo_Bar.X", id="pip-keeps-declared-name"),
    pytest.param("pip", None, "[extra]", "Foo_Bar.X", id="pip-with-extras"),
    pytest.param("uv", None, "[extra]", "foo-bar-x", id="uv-normalizes-name"),
    pytest.param(None, "uv", "", "foo-bar-x", id="uv-from-environment"),
]


@pytest.mark.parametrize(("backend", "env_backend", "extras", "expected"), _NAME_BY_BACKEND)
def test_package_name_from_spec_reads_static_name_without_building(
    tmp_path: Path, backend: str | None, env_backend: str | None, extras: str, expected: str
) -> None:
    # the build requirement does not exist, so any attempt to build the project would fail
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["no-such-build-backend"]\nbuild-backend = "hatchling.build"\n'
        '[project]\nname = "Foo_Bar.X"\n',
        encoding="utf-8",
    )

    assert (
        package_name_from_spec(
            f"{tmp_path}{extras}", sys.executable, pip_args=[], verbose=False, backend=backend, env_backend=env_backend
        )
        == expected
    )


@pytest.mark.parametrize(("backend", "env_backend", "extras", "expected"), _NAME_BY_BACKEND)
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


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "package_spec",
    [
        pytest.param("https://files.example/acme_tool-1.0-py3-none-any.whl", id="wheel-url"),
        pytest.param("acme-tool @ https://files.example/acme_tool-1.0-py3-none-any.whl", id="pep508-wheel-url"),
        pytest.param("git+https://git.example/acme-tool.git", id="vcs-url"),
    ],
)
@pytest.mark.usefixtures("lookalikes_below_cwd", "probe_venv")
def test_package_name_from_spec_ignores_files_below_cwd_named_like_url(package_spec: str) -> None:
    assert package_name_from_spec(package_spec, sys.executable, pip_args=[], verbose=False, backend=None) == "acme-tool"


@pytest.fixture
def lookalikes_below_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Path() collapses the URL's // so each file sits at the relative path one of the URLs below spells
    monkeypatch.chdir(tmp_path)
    for url_prefix in ("https:/files.example", "acme-tool @ https:/files.example"):
        (directory := tmp_path / url_prefix).mkdir(parents=True)
        with zipfile.ZipFile(directory / "acme_tool-1.0-py3-none-any.whl", "w") as archive:
            archive.writestr("x-0.dist-info/METADATA", "Name: other-app\n")
    (project := tmp_path / "git+https:/git.example/acme-tool.git").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n[project]\nname = "other-app"\n',
        encoding="utf-8",
    )


@pytest.fixture
def probe_venv(mocker: MockerFixture) -> MagicMock:
    venv: Final[MagicMock] = mocker.patch.object(common, "Venv", autospec=True)
    # Python 3.11's create_autospec drops a return value passed as a keyword for a child method
    venv.return_value.install_package_no_deps.return_value = "acme-tool"
    return venv


def test_package_name_from_spec_creates_probe_venv_with_pip_args(probe_venv: MagicMock) -> None:
    package_name_from_spec(
        "https://files.example/acme_tool-1.0-py3-none-any.whl",
        sys.executable,
        pip_args=["--index-url", "https://mirror.example/simple"],
        verbose=False,
        backend=None,
    )

    probe_venv.return_value.create_venv.assert_called_once_with(
        venv_args=[], pip_args=["--index-url", "https://mirror.example/simple"]
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_name_from_spec_builds_setup_py_project(local_extras_project: Path) -> None:
    assert (
        package_name_from_spec(f"{local_extras_project}[cow]", sys.executable, pip_args=[], verbose=False, backend=None)
        == "repeatme"
    )


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("app_named_before_last_dot")
def test_list_accepts_app_named_before_last_dot(capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()

    assert not run_pipx_cli(["list"])

    assert "unexpected location" not in capsys.readouterr().out


@pytest.fixture
def app_named_before_last_dot(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    dotted_app_wheel: Path,
) -> None:
    assert not run_pipx_cli(["install", "--suffix=@1", str(dotted_app_wheel)])
    # the name pipx 1.17.14 gave the app, with the suffix before the last dot
    (paths.CTX.bin_dir / "tool.12@1").rename(paths.CTX.bin_dir / "tool@1.12")


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("app_named_before_last_dot")
def test_expose_warns_when_renaming_app_named_before_last_dot(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["upgrade", "foo-bar-x@1"])

    assert "Renamed tool@1.12 to tool.12@1" in caplog.text


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["uninstall", "foo-bar-x@1"], id="uninstall"),
        pytest.param(["uninstall-all"], id="uninstall-all"),
        pytest.param(["reinstall-all"], id="reinstall-all"),
        pytest.param(["upgrade-all"], id="upgrade-all"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_copied_app_named_before_last_dot_is_removed(
    mocker: MockerFixture, dotted_app_wheel: Path, command: list[str]
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    assert not run_pipx_cli(["install", "--suffix=@1", str(dotted_app_wheel)])
    legacy: Final[Path] = (paths.CTX.bin_dir / "tool.12@1").rename(paths.CTX.bin_dir / "tool@1.12")

    assert not run_pipx_cli(command)

    assert not legacy.exists()


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["uninstall", "foo-bar-x@2"], id="uninstall"),
        pytest.param(["reinstall", "foo-bar-x@2"], id="reinstall"),
        pytest.param(["unexpose", "foo-bar-x@2"], id="unexpose"),
    ],
)
def test_copied_static_app_of_unsuffixed_venv_survives_suffixed_removal(
    static_scripts_wheel: Path, command: list[str]
) -> None:
    assert not run_pipx_cli(["install", str(static_scripts_wheel)])
    assert not run_pipx_cli(["install", "--suffix=@2", str(static_scripts_wheel)])

    assert not run_pipx_cli(command)

    assert (paths.CTX.bin_dir / "run.cmd").read_text(encoding="utf-8") == "echo static\n"


@pytest.fixture
def static_scripts_wheel(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    mocker: MockerFixture,
    make_wheel: Callable[[dict[str, str]], Path],
) -> Path:
    # scripts without a shebang copy byte for byte, so nothing in a copy says which venv exposed it
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    return make_wheel({
        "foo_bar_x-1.data/scripts/run": "echo static\n",
        "foo_bar_x-1.data/scripts/run.2": "echo static\n",
        "foo_bar_x-1.data/scripts/run.cmd": "echo static\n",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })


def test_copied_static_app_of_unsuffixed_venv_survives_suffixed_uninject(
    static_scripts_wheel: Path, empty_project_wheel: Path
) -> None:
    assert not run_pipx_cli(["install", str(static_scripts_wheel)])
    assert not run_pipx_cli(["install", "--suffix=@2", str(empty_project_wheel)])
    assert not run_pipx_cli(["inject", "empty-project@2", str(static_scripts_wheel), "--include-apps", "--with-suffix"])

    assert not run_pipx_cli(["uninject", "empty-project@2", "foo-bar-x"])

    assert (paths.CTX.bin_dir / "run.cmd").read_text(encoding="utf-8") == "echo static\n"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["uninstall", "foo-bar-xb"], id="uninstall"),
        pytest.param(["reinstall", "foo-bar-xb"], id="reinstall"),
    ],
)
def test_copied_static_app_named_like_another_venvs_legacy_name_survives(
    static_scripts_wheel: Path, command: list[str]
) -> None:
    # runb.2 is both the name pipx 1.17.14 gave run.2 under suffix b and the name run gets under suffix b.2
    assert not run_pipx_cli(["install", "--suffix=b", str(static_scripts_wheel)])
    assert not run_pipx_cli(["install", "--suffix=b.2", str(static_scripts_wheel)])

    assert not run_pipx_cli(command)

    assert (paths.CTX.bin_dir / "runb.2").read_text(encoding="utf-8") == "echo static\n"
