from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
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

    from pytest_mock import MockerFixture


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


@pytest.mark.parametrize(
    ("pin_args", "expected_pins"),
    [
        pytest.param([], (True, True), id="all"),
        pytest.param(["--injected-only"], (False, True), id="injected-only"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_restores_pins(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], pin_args: list[str], expected_pins: tuple[bool, bool]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay", *pin_args])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])

    assert not run_pipx_cli(["install-all", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (metadata.main_package.pinned, metadata.injected_packages["black"].pinned) == expected_pins


@pytest.fixture
def recorded_snapshot(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # create an isolated pipx home
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> tuple[Path, Path]:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    snapshot: Final = json.loads(capsys.readouterr().out)
    recorded: Final[Path] = tmp_path / "python-recorded"
    recorded.touch()
    snapshot["venvs"]["pycowsay"]["metadata"]["source_interpreter"] = {
        "__type__": "Path",
        "__Path__": str(recorded),
    }
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(json.dumps(snapshot), encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    return spec_file, recorded


@pytest.mark.parametrize(
    ("python_arg", "use_recorded"),
    [
        pytest.param([], True, id="recorded"),
        pytest.param(["--python", sys.executable], False, id="explicit"),
    ],
)
def test_install_all_selects_interpreter(
    recorded_snapshot: tuple[Path, Path],
    mocker: MockerFixture,
    python_arg: list[str],
    use_recorded: bool,
) -> None:
    spec_file, recorded = recorded_snapshot
    install: Final = mocker.patch("pipx.commands.install.install", autospec=True)
    assert not run_pipx_cli(["install-all", str(spec_file), *python_arg])
    assert Path(install.call_args.args[5]).resolve() == (recorded if use_recorded else Path(sys.executable).resolve())


def test_install_all_reports_missing_recorded_interpreter(
    recorded_snapshot: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    spec_file, recorded = recorded_snapshot
    recorded.unlink()
    assert not run_pipx_cli(["install-all", str(spec_file)])
    printed: Final[str] = " ".join(capsys.readouterr().out.split())
    assert "The exported python interpreter" in printed
    assert "is ignored as not found" in printed


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_force_ignores_explicit_python(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")

    assert not run_pipx_cli(["install-all", str(spec_file), "--force", "--python", sys.executable])
    assert "--python is ignored when --force is passed" in capsys.readouterr().out


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


@pytest.mark.parametrize(
    ("install_all_args", "expected_pip_args"),
    [
        pytest.param([], ["--no-cache-dir"], id="recorded"),
        pytest.param(["--pip-args=--no-compile"], ["--no-compile"], id="override"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_restores_recorded_args(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], install_all_args: list[str], expected_pip_args: list[str]
) -> None:
    assert not run_pipx_cli(["install", "--system-site-packages", "--pip-args=--no-cache-dir", "black"])
    assert not run_pipx_cli(["inject", "black", "--pip-args=--no-cache-dir", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])

    assert not run_pipx_cli(["install-all", *install_all_args, str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "black")
    assert (
        metadata.venv_args,
        metadata.main_package.pip_args,
        metadata.injected_packages["pycowsay"].pip_args,
    ) == (["--system-site-packages"], expected_pip_args, expected_pip_args)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_drops_recorded_pip_args_for_another_backend(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "--pip-args=--progress-bar off", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "--pip-args=--progress-bar off", PKG["black"]["spec"]])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (metadata.backend, metadata.main_package.pip_args, metadata.injected_packages["black"].pip_args) == (
        "uv",
        [],
        [],
    )


@pytest.fixture
def make_backend_snapshot(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> Callable[[str, str], Path]:
    def create(backend: str, pip_args: str) -> Path:
        assert not run_pipx_cli(["install", "--backend", backend, f"--pip-args={pip_args}", "pycowsay"])
        capsys.readouterr()
        assert not run_pipx_cli(["list", "--json"])
        (spec_file := tmp_path / "pipx.json").write_text(capsys.readouterr().out, encoding="utf-8")
        assert not run_pipx_cli(["uninstall-all"])
        return spec_file

    return create


@pytest.fixture
def credentialed_index_url(pipx_temp_env: None) -> str:  # ruff:ignore[unused-function-argument]  # it sets the index
    scheme, _, location = os.environ["PIP_INDEX_URL"].partition("://")
    return f"{scheme}://user:s3cret@{location}"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_warns_about_dropped_pip_args(
    make_backend_snapshot: Callable[[str, str], Path], caplog: pytest.LogCaptureFixture
) -> None:
    spec_file: Final[Path] = make_backend_snapshot("pip", "--progress-bar off")

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    assert "Ignoring pip args recorded for the pip backend of pycowsay: --progress-bar off\n" in caplog.text


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_warning_redacts_index_credentials(
    make_backend_snapshot: Callable[[str, str], Path], credentialed_index_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    spec_file: Final[Path] = make_backend_snapshot("pip", f"--progress-bar off --index-url {credentialed_index_url}")

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    redacted: Final[str] = credentialed_index_url.replace("s3cret", "****")
    assert (
        "Ignoring pip args recorded for the pip backend of pycowsay: --progress-bar off; translated for uv: "
        f"--default-index {redacted}\n"
    ) in caplog.text


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.parametrize(
    ("recorded_backend", "recorded_args", "expected_args"),
    [
        pytest.param("pip", "--index-url {url}", "--default-index {url}", id="pip-index-url"),
        pytest.param("pip", "--index-url={url}", "--default-index {url}", id="pip-joined-value"),
        pytest.param("pip", "-i{url}", "--default-index {url}", id="pip-short-joined-value"),
        pytest.param(
            "pip",
            "--extra-index-url {url} --find-links {links} --no-index",
            "--index {url} --find-links {links} --no-index",
            id="pip-extra-index-and-find-links",
        ),
        pytest.param(
            "pip",
            "--pre --trusted-host localhost -c {constraints} --keyring-provider disabled",
            "--prerelease allow --allow-insecure-host localhost --constraints {constraints} "
            "--keyring-provider disabled",
            id="pip-resolver-options",
        ),
        pytest.param("uv", "--default-index {url}", "--index-url {url}", id="uv-default-index"),
        pytest.param("uv", "--index=private={url}", "--extra-index-url {url}", id="uv-named-index"),
        pytest.param(
            "uv",
            "--no-index -f {links},{links}",
            "--no-index --find-links {links} --find-links {links}",
            id="uv-find-links-list",
        ),
        pytest.param(
            "uv",
            "--prerelease=allow --allow-insecure-host localhost --constraints {constraints}",
            "--pre --trusted-host localhost --constraint {constraints}",
            id="uv-resolver-options",
        ),
        pytest.param("uv", "--index-strategy unsafe-best-match", "", id="uv-pip-index-strategy"),
        pytest.param("uv", "--prerelease if-necessary", "", id="uv-prerelease-without-pip-equivalent"),
    ],
)
def test_install_all_translates_recorded_pip_args_for_another_backend(  # ruff:ignore[too-many-positional-arguments]  # pytest injects fixtures by name
    make_backend_snapshot: Callable[[str, str], Path],
    root: Path,
    tmp_path: Path,
    credentialed_index_url: str,
    recorded_backend: str,
    recorded_args: str,
    expected_args: str,
) -> None:
    (constraints := tmp_path / "constraints.txt").write_text("pycowsay\n", encoding="utf-8")
    values: Final[dict[str, str]] = {
        "url": credentialed_index_url,
        "links": str(root / ".pipx_tests" / "package_cache" / PACKAGE_CACHE_DIR_NAME),
        "constraints": str(constraints),
    }
    spec_file: Final[Path] = make_backend_snapshot(recorded_backend, recorded_args.format(**values))
    other_backend: Final[str] = "uv" if recorded_backend == "pip" else "pip"

    assert not run_pipx_cli(["install-all", "--backend", other_backend, str(spec_file)])

    assert PipxMetadata(paths.ctx.venvs / "pycowsay").main_package.pip_args == expected_args.format(**values).split()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.parametrize(
    ("recorded_backend", "recorded_args", "untranslatable"),
    [
        pytest.param("uv", "--index-strategy first-index", "--index-strategy first-index", id="uv-index-strategy"),
        pytest.param(
            "uv",
            "--allow-insecure-host http://localhost",
            "--allow-insecure-host http://localhost",
            id="uv-insecure-host-url",
        ),
        pytest.param("pip", "--keyring-provider import", "--keyring-provider import", id="pip-keyring-provider"),
    ],
)
def test_install_all_refuses_untranslatable_index_args(
    make_backend_snapshot: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    recorded_backend: str,
    recorded_args: str,
    untranslatable: str,
) -> None:
    spec_file: Final[Path] = make_backend_snapshot(recorded_backend, recorded_args)
    other_backend: Final[str] = "uv" if recorded_backend == "pip" else "pip"

    result: Final[int] = run_pipx_cli(["install-all", "--backend", other_backend, str(spec_file)])

    expected: Final[str] = (
        f"Cannot install pycowsay with the {other_backend} backend: its recorded index option {untranslatable} has "
        f"no {other_backend} equivalent, and dropping it could install from a different index."
    )
    assert (result, expected in " ".join(capsys.readouterr().err.split()), (paths.ctx.venvs / "pycowsay").exists()) == (
        1,
        True,
        False,
    )


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
        pytest.param(None, "Unable to read the spec metadata file {file}: No such file or directory", id="missing"),
        pytest.param(b"\xff", "The spec metadata file {file} is not valid JSON.", id="binary"),
        pytest.param(b"{", "The spec metadata file {file} is not valid JSON.", id="truncated"),
        pytest.param(b"[]", "The spec metadata file {file} is invalid.", id="not-an-object"),
        pytest.param(b'{"venvs": []}', "The spec metadata file {file} is invalid.", id="venvs-not-an-object"),
        pytest.param(b'{"venvs": {}}', "No packages found in the spec metadata file {file}.", id="no-venvs"),
        pytest.param(
            b'{"venvs": {"x": {}}}',
            "Entry 'x' in the spec metadata file {file} is missing 'metadata'.",
            id="no-metadata",
        ),
        pytest.param(
            b'{"venvs": {"x": {"metadata": {"pipx_metadata_version": "0.12"}}}}',
            "Entry 'x' in the spec metadata file {file} is missing 'main_package'.",
            id="no-main-package",
        ),
        pytest.param(
            b'{"venvs": {"x": {"metadata": "x"}}}',
            "Entry 'x' in the spec metadata file {file} is malformed: string indices must be integers, not 'str'",
            id="metadata-not-an-object",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_rejects_bad_spec_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes | None, expected_error: str
) -> None:
    spec_file: Final[Path] = tmp_path / "pipx.json"
    if content is not None:
        spec_file.write_bytes(content)

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    expected: Final[str] = " ".join(pipx_wrap(expected_error.format(file=spec_file)).split())
    assert (result, expected in error) == (1, True)


@pytest.fixture
def spec_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    for spec in ("pycowsay", PKG["pbr"]["spec"], PKG["black"]["spec"]):
        assert not run_pipx_cli(["install", spec])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])
    capsys.readouterr()
    return spec_file


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_prints_progress_in_spec_order(
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    spec_file: Path,
) -> None:
    venv_names: Final[list[str]] = list(json.loads(spec_file.read_text(encoding="utf-8"))["venvs"])
    before_venv_subprocess(paths.ctx.venvs / venv_names[0], lambda: time.sleep(0.3))

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert re.findall(r"^installing ([\w-]+)", capsys.readouterr().err, re.MULTILINE) == venv_names


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_installs_entries_before_a_malformed_one(spec_file: Path) -> None:
    spec: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    spec["venvs"] = {"pycowsay": spec["venvs"]["pycowsay"], "malformed": {}}
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    exit_code: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    assert (exit_code, sorted(venv_dir.name for venv_dir in paths.ctx.venvs.iterdir() if venv_dir.is_dir())) == (
        1,
        ["pycowsay"],
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_gives_shared_man_page_to_the_first_venv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    spec_file: Final[Path] = tmp_path / "pipx.json"
    spec_file.write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninstall-all"])
    first: Final[Path] = paths.ctx.venvs / next(iter(json.loads(spec_file.read_text(encoding="utf-8"))["venvs"]))
    before_venv_subprocess(first, lambda: time.sleep(0.5))

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(first)
