import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

import pytest
from pytest_mock import MockerFixture

from helpers import app_name, run_pipx_cli
from pipx import paths
from pipx.commands import manifest as manifest_module
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata


@pytest.fixture
def write_manifest(tmp_path: Path) -> Callable[[str], Path]:
    def write(content: str) -> Path:
        (manifest := tmp_path / "pipx.toml").write_text(content, encoding="utf-8")
        return manifest

    return write


def _manifest(package: str = "black", environment: str = "black", tool: str = "") -> str:
    tool_table = f"\n[tool.pipx.tools.{environment}]\n{tool}" if tool else ""
    return f"""[project]
name = "pipx-tools"
version = "1"
dependencies = []
requires-python = ">=3.10"

[dependency-groups]
{environment} = [{package!r}]

[tool.pipx]
version = "1.0"
{tool_table}
"""


def test_sync_manifest_installs_declared_tool(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
) -> None:
    manifest = write_manifest(
        _manifest(
            "pycowsay==0.0.0.2",
            "pycowsay-managed",
            'suffix = "-managed"\napps = ["pycowsay"]\ninclude-dependencies = false\nexpose = true\n',
        )
    )

    assert not run_pipx_cli(["manifest", "sync", str(manifest)])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay-managed")
    assert (
        metadata.main_package.package_or_url,
        metadata.main_package.suffix,
        metadata.main_package.expected_apps,
        (paths.ctx.bin_dir / app_name("pycowsay-managed")).is_file(),
    ) == ("pycowsay==0.0.0.2", "-managed", ["pycowsay"], True)


def test_sync_manifest_selects_dependency_apps(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    local_extras_project: Path,
) -> None:
    package: Final[str] = f"repeatme[tools] @ {local_extras_project.as_uri()}"
    manifest: Final[Path] = write_manifest(_manifest(package, "repeatme", 'include-resources-from = ["PyCowsay"]\n'))

    assert not run_pipx_cli(["manifest", "sync", str(manifest)])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_resources_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


def test_sync_manifest_prunes_undeclared_tool(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    manifest = write_manifest(_manifest("pycowsay", "pycowsay"))

    assert not run_pipx_cli(["manifest", "sync", "--prune", str(manifest)])

    assert not (paths.ctx.venvs / "black").exists()


def test_sync_manifest_hides_resources(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
) -> None:
    manifest = write_manifest(_manifest("pycowsay", "pycowsay", "expose = false\n"))

    assert not run_pipx_cli(["manifest", "sync", str(manifest)])

    assert (
        PipxMetadata(paths.ctx.venvs / "pycowsay").exposure_enabled,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
    ) == (False, False)


def test_sync_manifest_restores_environment_after_missing_app(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = write_manifest(_manifest("pycowsay", "pycowsay", 'apps = ["pycowsay"]\n'))
    assert not run_pipx_cli(["manifest", "sync", str(manifest)])
    (marker := paths.ctx.venvs / "pycowsay" / "marker").touch()
    write_manifest(_manifest("pycowsay", "pycowsay", 'apps = ["missing"]\n'))
    capsys.readouterr()

    assert run_pipx_cli(["manifest", "sync", str(manifest)])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        "Package pycowsay does not provide expected app missing" in capsys.readouterr().err,
        marker.exists(),
        metadata.main_package.expected_apps,
        metadata.exposure_enabled,
        (paths.ctx.bin_dir / app_name("pycowsay")).is_file(),
    ) == (True, True, ["pycowsay"], True, True)


def test_sync_manifest_reapplies_lock(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    make_pylock: Callable[[str, str], Path],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    manifest = write_manifest(_manifest("pycowsay>=0", "pycowsay", f'apps = ["pycowsay"]\nlock = "{lock_file.name}"\n'))
    assert not run_pipx_cli(["manifest", "sync", str(manifest)])
    (marker := paths.ctx.venvs / "pycowsay" / "marker").touch()

    assert not run_pipx_cli(["manifest", "sync", str(manifest)])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (metadata.package_version, metadata.lock_file, marker.exists()) == (
        "0.0.0.2",
        lock_file.resolve(),
        False,
    )


def test_sync_manifest_clears_app_and_lock_state(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    make_pylock: Callable[[str, str], Path],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    manifest = write_manifest(_manifest("pycowsay", "pycowsay", f'apps = ["pycowsay"]\nlock = "{lock_file.name}"\n'))
    assert not run_pipx_cli(["manifest", "sync", str(manifest)])
    (marker := paths.ctx.venvs / "pycowsay" / "marker").touch()
    write_manifest(_manifest("pycowsay", "pycowsay"))

    assert not run_pipx_cli(["manifest", "sync", str(manifest)])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay").main_package
    assert (metadata.expected_apps, metadata.lock_file, marker.exists()) == ([], None, False)


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
        pytest.param("invalid", "Cannot read manifest", id="toml"),
        pytest.param(_manifest() + "\n[extra]\n", "Unknown manifest table", id="root"),
        pytest.param("project = []\n", "Manifest project must be a table", id="project-type"),
        pytest.param(
            _manifest().replace("dependencies = []", "dependencies = []\nextra = true"),
            "Unknown manifest project key",
            id="project-key",
        ),
        pytest.param(
            _manifest().replace('name = "pipx-tools"', "name = 1"),
            "requires string name and version",
            id="project-name",
        ),
        pytest.param(
            _manifest().replace("dependencies = []", 'dependencies = ["black"]'),
            "project dependencies must be empty",
            id="project-dependencies",
        ),
        pytest.param(
            _manifest().replace('requires-python = ">=3.10"', "requires-python = true"),
            "requires-python must be a string",
            id="requires-python",
        ),
        pytest.param(
            _manifest().replace("black = ['black']", ""),
            "dependency-groups must be a non-empty table",
            id="groups-empty",
        ),
        pytest.param(
            _manifest().replace("black = ['black']", 'black = "black"'),
            "must contain one package requirement",
            id="group-type",
        ),
        pytest.param(
            _manifest().replace("black = ['black']", "black = ['black', 'ruff']"),
            "must contain one package requirement",
            id="group-size",
        ),
        pytest.param(
            _manifest().replace("black = ['black']", "black = [1]"),
            "must contain one package requirement",
            id="group-package",
        ),
        pytest.param(
            _manifest().replace('[tool.pipx]\nversion = "1.0"', "tool = []"),
            "Manifest tool must be a table",
            id="tool-type",
        ),
        pytest.param(_manifest() + "\n[tool.other]\n", "Unknown manifest tool table", id="tool-table"),
        pytest.param(_manifest() + "\n[tool]\nnab = true\n", "tool.nab must be a table", id="nab"),
        pytest.param(
            _manifest().replace('[tool.pipx]\nversion = "1.0"', "[tool.nab]"),
            "tool.pipx must be a table",
            id="pipx-missing",
        ),
        pytest.param(
            _manifest().replace('[tool.pipx]\nversion = "1.0"', "[tool]\npipx = true"),
            "tool.pipx must be a table",
            id="pipx-type",
        ),
        pytest.param(_manifest() + "unknown = true\n", "Unknown tool.pipx key", id="pipx-key"),
        pytest.param(_manifest().replace('version = "1.0"', 'version = "2.0"'), "Manifest version", id="version"),
        pytest.param(_manifest() + "tools = []\n", "tool.pipx.tools must be a table", id="tools-type"),
        pytest.param(
            _manifest() + "\n[tool.pipx.tools.ruff]\n",
            "Missing dependency groups for manifest tools",
            id="tool-group",
        ),
        pytest.param(
            _manifest() + '\n[tool.pipx.tools]\nblack = "black"\n',
            "Manifest tool black must be a table",
            id="tool-value",
        ),
        pytest.param(_manifest("black", "Black"), "must be normalized", id="name"),
        pytest.param(
            _manifest("black", "black", "unknown = true\n"),
            "Unknown key for manifest tool black",
            id="tool-key",
        ),
        pytest.param(_manifest("["), "invalid package requirement", id="package"),
        pytest.param(
            _manifest('black; python_version > "3.10"'),
            "cannot use an environment marker",
            id="marker",
        ),
        pytest.param(
            _manifest("black", "black-other", 'suffix = "-one"\n'),
            "must match package black",
            id="environment",
        ),
        pytest.param(_manifest("black", "black", "suffix = true\n"), "suffix must be a string", id="suffix"),
        pytest.param(
            _manifest("black", "black", 'apps = "black"\n'),
            "apps must be non-empty strings",
            id="apps-type",
        ),
        pytest.param(
            _manifest("black", "black", 'apps = [""]\n'),
            "apps must be non-empty strings",
            id="app-empty",
        ),
        pytest.param(
            _manifest("black", "black", 'apps = ["black", "black"]\n'),
            "apps must be unique",
            id="apps-duplicate",
        ),
        pytest.param(
            _manifest("black", "black", 'include-dependencies = "yes"\n'),
            "include-dependencies must be a boolean",
            id="include-dependencies",
        ),
        pytest.param(
            _manifest("black", "black", 'include-resources-from = "pycowsay"\n'),
            "include-resources-from must be non-empty strings",
            id="include-resources-from-type",
        ),
        pytest.param(
            _manifest("black", "black", 'include-resources-from = [""]\n'),
            "include-resources-from must be non-empty strings",
            id="include-resources-from-empty",
        ),
        pytest.param(
            _manifest("black", "black", 'include-resources-from = ["PyCowsay", "pycowsay"]\n'),
            "include-resources-from must be unique",
            id="include-resources-from-duplicate",
        ),
        pytest.param(
            _manifest(
                "black",
                "black",
                'include-dependencies = true\ninclude-resources-from = ["pycowsay"]\n',
            ),
            "cannot combine include-dependencies",
            id="include-resources-from-all",
        ),
        pytest.param(
            _manifest("black", "black", 'expose = "yes"\n'),
            "expose must be a boolean",
            id="expose",
        ),
        pytest.param(_manifest("black", "black", "lock = 1\n"), "lock must be a path string", id="lock-type"),
        pytest.param(
            _manifest("black", "black", 'lock = "black.lock"\n'),
            "lock must be named",
            id="lock-name",
        ),
        pytest.param(
            _manifest("black", "black", 'lock = "pylock.black.toml"\n'),
            "Lock file does not exist",
            id="lock-missing",
        ),
    ],
)
def test_sync_manifest_rejects_invalid_input(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
    content: str,
    expected_error: str,
) -> None:
    assert run_pipx_cli(["manifest", "sync", str(write_manifest(content))])
    assert expected_error in capsys.readouterr().err


@pytest.mark.parametrize("path_kind", [pytest.param("missing", id="missing"), pytest.param("directory", id="directory")])
def test_sync_manifest_rejects_unreadable_path(
    pipx_temp_env: None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    path_kind: Literal["missing", "directory"],
) -> None:
    manifest = tmp_path / "missing.toml"
    if path_kind == "directory":
        manifest.mkdir()

    assert run_pipx_cli(["manifest", "sync", str(manifest)])

    assert ("does not exist" if path_kind == "missing" else "Cannot read manifest") in capsys.readouterr().err


def test_sync_manifest_rejects_duplicate_locks(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "pylock.tools.toml").touch()
    manifest = write_manifest(
        """[project]
name = "pipx-tools"
version = "1"
dependencies = []

[dependency-groups]
black = ["black"]
pycowsay = ["pycowsay"]

[tool.pipx]
version = "1.0"

[tool.pipx.tools.black]
lock = "pylock.tools.toml"

[tool.pipx.tools.pycowsay]
lock = "pylock.tools.toml"
"""
    )

    assert run_pipx_cli(["manifest", "sync", str(manifest)])
    assert "Lock files must be unique per tool" in capsys.readouterr().err


def test_lock_manifest_generates_named_locks(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = write_manifest(
        """[project]
name = "pipx-tools"
version = "1"
dependencies = []

[dependency-groups]
black = ["black>=22,<23"]
pycowsay = ["pycowsay"]

[tool.pipx]
version = "1.0"

[tool.pipx.tools.black]
lock = "locks/pylock.toml"

[tool.nab]
offline = false
"""
    )
    (lock_file := tmp_path / "locks" / "pylock.toml").parent.mkdir()
    lock_file.write_text("old\n", encoding="utf-8")
    observed: list[tuple[str, str, str]] = []

    def run_nab(command: list[str], *, check: bool, cwd: Path) -> subprocess.CompletedProcess[str]:
        generated_lock = Path(command[6])
        observed.append((Path(command[2]).read_text(encoding="utf-8"), command[4], generated_lock.read_text()))
        generated_lock.write_text('lock-version = "1.0"\ncreated-by = "nab"\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    mocker.patch.object(manifest_module, "which", autospec=True, return_value="/usr/bin/nab")
    run = mocker.patch.object(manifest_module.subprocess, "run", autospec=True, side_effect=run_nab)

    assert not run_pipx_cli(["manifest", "lock", str(manifest)])

    assert (
        run.call_count,
        observed,
        lock_file.read_text(encoding="utf-8"),
        "locked" in capsys.readouterr().out,
    ) == (
        1,
        [(manifest.read_text(encoding="utf-8"), "black", "old\n")],
        'lock-version = "1.0"\ncreated-by = "nab"\n',
        True,
    )


@pytest.mark.parametrize(
    ("mode", "expected_error"),
    [
        pytest.param("failure", "nab failed to lock black", id="failure"),
        pytest.param("missing", "nab did not create pylock.toml", id="missing-output"),
        pytest.param("os-error", "Cannot write manifest locks: unavailable", id="os-error"),
    ],
)
def test_lock_manifest_preserves_existing_lock_after_failure(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
    mode: Literal["failure", "missing", "os-error"],
    expected_error: str,
) -> None:
    manifest = write_manifest(_manifest("black", "black", 'lock = "pylock.toml"\n'))
    (lock_file := tmp_path / "pylock.toml").write_text("old\n", encoding="utf-8")

    def run_nab(command: list[str], *, check: bool, cwd: Path) -> subprocess.CompletedProcess[str]:
        if mode == "failure":
            return subprocess.CompletedProcess(command, 1)
        if mode == "os-error":
            raise OSError("unavailable")
        Path(command[6]).unlink()
        return subprocess.CompletedProcess(command, 0)

    mocker.patch.object(manifest_module, "which", autospec=True, return_value="/usr/bin/nab")
    mocker.patch.object(manifest_module.subprocess, "run", autospec=True, side_effect=run_nab)

    assert run_pipx_cli(["manifest", "lock", str(manifest)])

    assert (expected_error in capsys.readouterr().err, lock_file.read_text(encoding="utf-8")) == (True, "old\n")


def test_lock_manifest_rolls_back_every_lock_when_one_replacement_fails(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    tmp_path: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = write_manifest(
        """[project]
name = "pipx-tools"
version = "1"
dependencies = []

[dependency-groups]
black = ["black>=22,<23"]
pycowsay = ["pycowsay"]

[tool.pipx]
version = "1.0"

[tool.pipx.tools.black]
lock = "pylock.black.toml"

[tool.pipx.tools.pycowsay]
lock = "pylock.pycowsay.toml"

[tool.nab]
offline = false
"""
    )
    (tmp_path / "pylock.black.toml").write_text("old-black\n", encoding="utf-8")
    (tmp_path / "pylock.pycowsay.toml").write_text("old-pycowsay\n", encoding="utf-8")

    def run_nab(command: list[str], *, check: bool, cwd: Path) -> subprocess.CompletedProcess[str]:
        Path(command[6]).write_text("new\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    mocker.patch.object(manifest_module, "which", autospec=True, return_value="/usr/bin/nab")
    mocker.patch.object(manifest_module.subprocess, "run", autospec=True, side_effect=run_nab)

    real_replace = Path.replace
    swap_ins = {"count": 0}

    def replace(self: Path, target: Path) -> Path:
        source, destination = Path(self), Path(target)
        if destination.name.startswith("pylock") and ".previous" not in destination.parts + source.parts:
            swap_ins["count"] += 1
            if swap_ins["count"] == 2:
                raise OSError("replace failed")
        return real_replace(self, target)

    mocker.patch.object(Path, "replace", autospec=True, side_effect=replace)

    assert run_pipx_cli(["manifest", "lock", str(manifest)])

    assert (
        "Cannot write manifest locks" in capsys.readouterr().err,
        (tmp_path / "pylock.black.toml").read_text(encoding="utf-8"),
        (tmp_path / "pylock.pycowsay.toml").read_text(encoding="utf-8"),
    ) == (True, "old-black\n", "old-pycowsay\n")


@pytest.mark.parametrize(
    ("nab", "lock", "expected_error"),
    [
        pytest.param(None, 'lock = "pylock.toml"\n', "nab command is required", id="nab"),
        pytest.param("/usr/bin/nab", "", "does not declare any lock files", id="lock"),
    ],
)
def test_lock_manifest_requires_nab_and_lock(
    pipx_temp_env: None,
    write_manifest: Callable[[str], Path],
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
    nab: str | None,
    lock: str,
    expected_error: str,
) -> None:
    manifest = write_manifest(_manifest("black", "black", lock))
    mocker.patch.object(manifest_module, "which", autospec=True, return_value=nab)

    assert run_pipx_cli(["manifest", "lock", str(manifest)])
    assert expected_error in capsys.readouterr().err
