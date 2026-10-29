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
from packaging.utils import canonicalize_name

from helpers import current_log_file, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata
from pipx.wrap import pipx_wrap

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
def test_install_all(
    *,
    package_cache_dir: Path,
    capsys: pytest.CaptureFixture[str],
    make_pylock: Callable[[str, str], Path],
    make_snapshot: Callable[[list[list[str]]], Path],
    install_all_args: list[str],
    expected_cooldown: int,
) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    spec_file: Final[Path] = make_snapshot([
        ["install", "--app", "pycowsay", "--lock", str(lock_file), "pycowsay"],
        ["install", "--cooldown", "7", pip_args, PKG["black"]["spec"]],
        ["inject", "black", pip_args, "pycowsay"],
    ])

    assert not run_pipx_cli(["install-all", *install_all_args, pip_args, str(spec_file)])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])

    installed_names: Final[list[str]] = sorted(json.loads(capsys.readouterr().out)["venvs"])
    black_metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "black")
    pycowsay_metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
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


@pytest.fixture
def make_snapshot(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> Callable[[list[list[str]]], Path]:
    def create(commands: list[list[str]]) -> Path:
        for command in commands:
            assert not run_pipx_cli(command)
        capsys.readouterr()
        assert not run_pipx_cli(["list", "--json"])
        (spec_file := tmp_path / "pipx.json").write_text(capsys.readouterr().out, encoding="utf-8")
        assert not run_pipx_cli(["uninstall-all"])
        capsys.readouterr()
        return spec_file

    return create


@pytest.mark.parametrize(
    ("pin_args", "expected_pins"),
    [
        pytest.param([], (True, True), id="all"),
        pytest.param(["--injected-only"], (False, True), id="injected-only"),
    ],
)
def test_install_all_restores_pins(
    make_snapshot: Callable[[list[list[str]]], Path], pin_args: list[str], expected_pins: tuple[bool, bool]
) -> None:
    spec_file: Final[Path] = make_snapshot([
        ["install", "pycowsay"],
        ["inject", "pycowsay", PKG["black"]["spec"]],
        ["pin", "pycowsay", *pin_args],
    ])

    assert not run_pipx_cli(["install-all", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (metadata.main_package.pinned, metadata.injected_packages["black"].pinned) == expected_pins


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
    assert Path(install.call_args.args[3].python).resolve() == (
        recorded if use_recorded else Path(sys.executable).resolve()
    )


@pytest.fixture
def recorded_snapshot(make_snapshot: Callable[[list[list[str]]], Path], tmp_path: Path) -> tuple[Path, Path]:
    spec_file: Final[Path] = make_snapshot([["install", "pycowsay"]])
    snapshot: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    (recorded := tmp_path / "python-recorded").touch()
    snapshot["venvs"]["pycowsay"]["metadata"]["source_interpreter"] = {"__type__": "Path", "__Path__": str(recorded)}
    spec_file.write_text(json.dumps(snapshot), encoding="utf-8")
    return spec_file, recorded


def test_install_all_reports_missing_recorded_interpreter(
    recorded_snapshot: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    spec_file, recorded = recorded_snapshot
    recorded.unlink()
    assert not run_pipx_cli(["install-all", str(spec_file)])
    printed: Final[str] = " ".join(capsys.readouterr().out.split())
    assert ("The exported python interpreter" in printed, "is ignored as not found" in printed) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_force_ignores_explicit_python(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    (spec_file := tmp_path / "pipx.json").write_text(capsys.readouterr().out, encoding="utf-8")

    assert not run_pipx_cli(["install-all", str(spec_file), "--force", "--python", sys.executable])
    assert "pipx ignores --python when you pass --force" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_multiple_errors(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pipx_metadata_path: Final[Path] = root / "testdata" / "pipx_metadata_multiple_errors.json"
    assert run_pipx_cli(["install-all", str(pipx_metadata_path)])
    captured: Final = capsys.readouterr()
    log_file: Final[Path] = current_log_file()
    pip_errors: Final[str] = log_file.with_name(f"{log_file.stem}_pip_errors.log").read_text(encoding="utf-8")
    assert (
        "The following package(s) failed to install: dotenv, weblate" in captured.err,
        f"No packages installed after running 'pipx install-all {pipx_metadata_path}'" in captured.out,
        "dotenv" in pip_errors,
        "weblate" in pip_errors,
    ) == (True, True, True, True)


def test_install_all_reports_injected_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], make_snapshot: Callable[[list[list[str]]], Path]
) -> None:
    spec_file: Final[Path] = make_snapshot([["install", "black"], ["inject", "black", "pycowsay"]])
    missing_spec: Final[str] = (tmp_path / "missing").as_posix()
    spec_file.write_text(
        spec_file.read_text(encoding="utf-8").replace(
            '"package_or_url": "pycowsay"', f'"package_or_url": "{missing_spec}"'
        ),
        encoding="utf-8",
    )

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
def test_install_all_restores_recorded_args(
    make_snapshot: Callable[[list[list[str]]], Path], install_all_args: list[str], expected_pip_args: list[str]
) -> None:
    spec_file: Final[Path] = make_snapshot([
        ["install", "--system-site-packages", "--pip-args=--no-cache-dir", "black"],
        ["inject", "black", "--pip-args=--no-cache-dir", "pycowsay"],
    ])

    assert not run_pipx_cli(["install-all", *install_all_args, str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "black")
    assert (
        metadata.venv_args,
        metadata.main_package.pip_args,
        metadata.injected_packages["pycowsay"].pip_args,
    ) == (["--system-site-packages"], expected_pip_args, expected_pip_args)


def test_install_all_leaves_directory_named_in_recorded_venv_args(
    tmp_path: Path, make_snapshot: Callable[[list[list[str]]], Path]
) -> None:
    spec_file: Final[Path] = make_snapshot([["install", "--backend", "pip", "pycowsay"]])
    spec: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    (other_dir := tmp_path / "documents").mkdir()
    (other_dir / "notes.txt").write_text("keep", encoding="utf-8")
    spec["venvs"]["pycowsay"]["metadata"]["venv_args"] = ["--clear", str(other_dir)]
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert sorted(path.name for path in other_dir.iterdir()) == ["notes.txt"]


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_drops_recorded_pip_args_for_another_backend(
    make_snapshot: Callable[[list[list[str]]], Path],
) -> None:
    spec_file: Final[Path] = make_snapshot([
        ["install", "--backend", "pip", "--pip-args=--progress-bar off", "pycowsay"],
        ["inject", "pycowsay", "--pip-args=--progress-bar off", PKG["black"]["spec"]],
    ])

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (metadata.backend, metadata.main_package.pip_args, metadata.injected_packages["black"].pip_args) == (
        "uv",
        [],
        [],
    )


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_warns_about_dropped_pip_args(
    make_snapshot: Callable[[list[list[str]]], Path], caplog: pytest.LogCaptureFixture
) -> None:
    spec_file: Final[Path] = make_snapshot([
        ["install", "--backend", "pip", "--pip-args=--progress-bar off", "pycowsay"]
    ])

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    assert "Ignoring pip args recorded for the pip backend of pycowsay: --progress-bar off\n" in caplog.text


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_keeps_ambiguous_pip_abbreviation_as_typed(
    make_snapshot: Callable[[list[list[str]]], Path], caplog: pytest.LogCaptureFixture
) -> None:
    # pip rejects --pr, a prefix of --pre, --prefix and --progress-bar, so it must not replay as uv's --prerelease
    spec_file: Final[Path] = make_snapshot([["install", "--backend", "pip", "--pip-args=--pre", "pycowsay"]])
    spec_file.write_text(spec_file.read_text(encoding="utf-8").replace('"--pre"', '"--pr"'), encoding="utf-8")

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    assert (
        "Ignoring pip args recorded for the pip backend of pycowsay: --pr\n" in caplog.text,
        PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args,
    ) == (True, [])


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_all_warning_redacts_index_credentials(
    make_snapshot: Callable[[list[list[str]]], Path], credentialed_index_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    spec_file: Final[Path] = make_snapshot([
        [
            "install",
            "--backend",
            "pip",
            f"--pip-args=--progress-bar off --index-url {credentialed_index_url}",
            "pycowsay",
        ]
    ])

    assert not run_pipx_cli(["install-all", "--backend", "uv", str(spec_file)])

    redacted: Final[str] = credentialed_index_url.replace("user:s3cret", "****:****")
    assert (
        "Ignoring pip args recorded for the pip backend of pycowsay: --progress-bar off; translated for uv: "
        f"--default-index {redacted}\n"
    ) in caplog.text


@pytest.fixture
def credentialed_index_url(pipx_temp_env: None) -> str:  # ruff:ignore[unused-function-argument]  # it sets the index
    scheme, _, location = os.environ["PIP_INDEX_URL"].partition("://")
    return f"{scheme}://user:s3cret@{location}"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
@pytest.mark.parametrize(
    ("recorded_backend", "recorded_args", "expected_args"),
    [
        pytest.param("pip", "--index-url {url}", "--default-index {url}", id="pip-index-url"),
        pytest.param("pip", "--index-url={url}", "--default-index {url}", id="pip-joined-value"),
        pytest.param("pip", "-i{url}", "--default-index {url}", id="pip-short-joined-value"),
        pytest.param("pip", "--index-u {url}", "--default-index {url}", id="pip-abbreviated-index-url"),
        pytest.param("pip", "--index={url}", "--default-index {url}", id="pip-index-abbreviates-index-url"),
        pytest.param(
            "pip",
            "--extra-i {url} --find-l {links} --no-ind --tr localhost",
            "--index {url} --find-links {links} --no-index --allow-insecure-host localhost",
            id="pip-abbreviated-options",
        ),
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
def test_install_all_translates_recorded_pip_args_for_another_backend(
    *,
    make_snapshot: Callable[[list[list[str]]], Path],
    package_cache_dir: Path,
    tmp_path: Path,
    credentialed_index_url: str,
    recorded_backend: str,
    recorded_args: str,
    expected_args: str,
) -> None:
    (constraints := tmp_path / "constraints.txt").write_text("pycowsay\n", encoding="utf-8")
    values: Final[dict[str, str]] = {
        "url": credentialed_index_url,
        "links": str(package_cache_dir),
        "constraints": str(constraints),
    }
    spec_file: Final[Path] = make_snapshot([
        ["install", "--backend", recorded_backend, f"--pip-args={recorded_args.format(**values)}", "pycowsay"]
    ])

    assert not run_pipx_cli(["install-all", "--backend", "uv" if recorded_backend == "pip" else "pip", str(spec_file)])

    assert PipxMetadata(paths.CTX.venvs / "pycowsay").main_package.pip_args == expected_args.format(**values).split()


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
        pytest.param("pip", "--keyring-p import", "--keyring-provider import", id="pip-abbreviated-keyring-provider"),
    ],
)
def test_install_all_refuses_untranslatable_index_args(
    make_snapshot: Callable[[list[list[str]]], Path],
    capsys: pytest.CaptureFixture[str],
    recorded_backend: str,
    recorded_args: str,
    untranslatable: str,
) -> None:
    spec_file: Final[Path] = make_snapshot([
        ["install", "--backend", recorded_backend, f"--pip-args={recorded_args}", "pycowsay"]
    ])
    other_backend: Final[str] = "uv" if recorded_backend == "pip" else "pip"

    result: Final[int] = run_pipx_cli(["install-all", "--backend", other_backend, str(spec_file)])

    expected: Final[str] = (
        f"Cannot install pycowsay with the {other_backend} backend: its recorded index option {untranslatable} has "
        f"no {other_backend} equivalent, and dropping it could install from a different index."
    )
    assert (result, expected in " ".join(capsys.readouterr().err.split()), (paths.CTX.venvs / "pycowsay").exists()) == (
        1,
        True,
        False,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_rejects_missing_spec_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    spec_file: Final[Path] = tmp_path / "pipx.json"

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    expected: Final[str] = " ".join(
        pipx_wrap(f"Unable to read the spec metadata file {spec_file}: No such file or directory").split()
    )
    assert (result, expected in " ".join(capsys.readouterr().err.split())) == (1, True)


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
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
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes, expected_error: str
) -> None:
    (spec_file := tmp_path / "pipx.json").write_bytes(content)

    result: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    error: Final[str] = " ".join(capsys.readouterr().err.split())
    expected: Final[str] = " ".join(pipx_wrap(expected_error.format(file=spec_file)).split())
    assert (result, expected in error) == (1, True)


def test_install_all_prints_progress_in_spec_order(
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    spec_file: Path,
) -> None:
    venv_names: Final[list[str]] = list(json.loads(spec_file.read_text(encoding="utf-8"))["venvs"])
    before_venv_subprocess(paths.CTX.venvs / venv_names[0], lambda: time.sleep(0.3))

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert re.findall(r"^installing ([\w-]+)", capsys.readouterr().err, re.MULTILINE) == venv_names


@pytest.fixture
def spec_file(make_snapshot: Callable[[list[list[str]]], Path]) -> Path:
    return make_snapshot([["install", spec] for spec in ("pycowsay", PKG["pbr"]["spec"], PKG["black"]["spec"])])


def test_install_all_refuses_an_environment_name_outside_the_store(spec_file: Path, tmp_path: Path) -> None:
    spec: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    spec["venvs"] = {"pycowsay": spec["venvs"]["pycowsay"]}
    spec["venvs"]["pycowsay"]["metadata"]["main_package"]["package"] = str(tmp_path / "outside")
    spec_file.write_text(json.dumps(spec), encoding="utf-8")
    # pipx canonicalizes the name before it becomes a directory
    outside: Final[Path] = Path(canonicalize_name(str(tmp_path / "outside")))

    assert (run_pipx_cli(["install-all", str(spec_file)]), outside.exists()) == (1, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_all_leaves_injected_packages_of_a_skipped_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["pbr"]["spec"]])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--json"])
    (spec_file := tmp_path / "pipx.json").write_text(capsys.readouterr().out, encoding="utf-8")
    assert not run_pipx_cli(["uninject", "pycowsay", "pbr"])

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert list(PipxMetadata(paths.CTX.venvs / "pycowsay").injected_packages) == []


def test_install_all_installs_entries_before_a_malformed_one(spec_file: Path) -> None:
    spec: Final = json.loads(spec_file.read_text(encoding="utf-8"))
    spec["venvs"] = {"pycowsay": spec["venvs"]["pycowsay"], "malformed": {}}
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    exit_code: Final[int] = run_pipx_cli(["install-all", str(spec_file)])

    assert (exit_code, sorted(venv_dir.name for venv_dir in paths.CTX.venvs.iterdir() if venv_dir.is_dir())) == (
        1,
        ["pycowsay"],
    )


def test_install_all_gives_shared_man_page_to_the_first_venv(
    make_snapshot: Callable[[list[list[str]]], Path],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
) -> None:
    spec_file: Final[Path] = make_snapshot([["install", "pycowsay"], ["install", "pycowsay", "--suffix=_x"]])
    first: Final[Path] = paths.CTX.venvs / next(iter(json.loads(spec_file.read_text(encoding="utf-8"))["venvs"]))
    before_venv_subprocess(first, lambda: time.sleep(0.5))

    assert not run_pipx_cli(["install-all", str(spec_file)])

    assert (paths.CTX.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(first)
