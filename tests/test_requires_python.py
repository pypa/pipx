from __future__ import annotations

import json
import os
import shutil
import sys
from typing import TYPE_CHECKING, Final

import pytest
from packaging.specifiers import SpecifierSet

from helpers import run_pipx_cli
from pipx import paths
from pipx.constants import MINIMUM_PYTHON_VERSION, FetchPythonOptions
from pipx.interpreter import InterpreterResolutionError
from pipx.pipx_metadata_file import PipxMetadata
from pipx.requires_python import interpreter_for, rejected_constraint, unsatisfied_constraint
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param(
            "ERROR: Package 'oldpkg' requires a different Python: 3.14.6 not in '<3.12'",
            "<3.12",
            id="rejection",
        ),
        pytest.param(
            "ERROR: Package 'x' requires a different Python: 3.14.6 not in '>=3.9,<3.12'",
            "<3.12,>=3.9",
            id="two-clauses",
        ),
        pytest.param(
            "  cause: Because the current Python version (3.11.17) does not satisfy Python>=3.12 and x==1 depends on",
            ">=3.12",
            id="uv-rejection",
        ),
        pytest.param(
            "  cause: Because the current Python version (3.11.17) does not satisfy\n         Python>=3.12,<3.16, we",
            "<3.16,>=3.12",
            id="uv-wrapped-two-clauses",
        ),
        pytest.param(
            "  cause: Because the current Python version (3.11.17) does not satisfy all of:\n"
            "             Python>=3.12,<3.15\n             Python>=3.16\n         and x==0.1 depends on one of:",
            "<3.15,>=3.12",
            id="uv-union",
        ),
        pytest.param(
            "  cause: Because the current Python version (3.11.17) does not satisfy all of:\n"
            "             Python>=3.12,<3.13\n             Python>=3.14\n         and x==0.1 depends on one of:",
            ">=3.14",
            id="uv-union-newest-range",
        ),
        pytest.param(
            "  cause: Because the current Python version (3.11.17) does not satisfy all of:\n"
            "             Python>=3.20,<3.21\n             Python>=3.22\n",
            "<3.21,>=3.20",
            id="uv-union-beyond-pipx",
        ),
        pytest.param("ERROR: No matching distribution found for oldpkg", None, id="other-error"),
        pytest.param("", None, id="empty"),
    ],
)
def test_rejected_constraint_reads_the_backend_complaint(output: str, expected: str | None) -> None:
    constraint: Final[SpecifierSet | None] = rejected_constraint(output)

    assert (None if constraint is None else str(constraint)) == expected


@pytest.mark.parametrize(
    ("requires_python", "python_version", "expected"),
    [
        pytest.param("<3.12", "3.14.6", "<3.12", id="violated"),
        pytest.param("<3.12", "3.11.9", None, id="satisfied"),
        pytest.param(None, "3.14.6", None, id="undeclared"),
        pytest.param("", "3.14.6", None, id="empty"),
        pytest.param("not-a-specifier", "3.14.6", None, id="unreadable"),
    ],
)
def test_unsatisfied_constraint_reports_only_a_mismatch(
    requires_python: str | None,
    python_version: str,
    expected: str | None,
) -> None:
    constraint: Final[SpecifierSet | None] = unsatisfied_constraint(requires_python, python_version)

    assert (None if constraint is None else str(constraint)) == expected


def _install(mocker: MockerFixture, installed: dict[str, str], *, fetched: dict[str, str] | None = None) -> None:
    """Fake a system where minor ``X.Y`` resolves to the given full version; missing minors download ``fetched``."""
    fetched = fetched or {}

    def resolve(minor: str, fetch: FetchPythonOptions) -> str:
        if minor in installed:
            return f"/py/{installed[minor]}"
        if fetch is FetchPythonOptions.MISSING and minor in fetched:
            return f"/downloaded/{fetched[minor]}"
        raise InterpreterResolutionError(source="the system", version=minor)

    mocker.patch("pipx.requires_python.find_python_interpreter", side_effect=resolve)
    mocker.patch("pipx.requires_python._interpreter_version", side_effect=lambda path: path.rsplit("/", 1)[1])


def test_interpreter_for_takes_the_newest_installed_match(mocker: MockerFixture) -> None:
    _install(mocker, {"3.11": "3.11.9", "3.10": "3.10.14"})

    assert interpreter_for(SpecifierSet("<3.12"), FetchPythonOptions.NEVER) == "/py/3.11.9"


def test_interpreter_for_skips_a_version_the_system_lacks(mocker: MockerFixture) -> None:
    _install(mocker, {"3.11": "3.11.9"})

    assert interpreter_for(SpecifierSet("<3.13"), FetchPythonOptions.NEVER) == "/py/3.11.9"


def test_interpreter_for_accepts_a_patch_above_a_lower_bound(mocker: MockerFixture) -> None:
    _install(mocker, {"3.13": "3.13.7"})

    assert interpreter_for(SpecifierSet(">=3.13.5,<3.14"), FetchPythonOptions.NEVER) == "/py/3.13.7"


def test_interpreter_for_rejects_a_patch_above_an_upper_bound(mocker: MockerFixture) -> None:
    _install(mocker, {"3.14": "3.14.6", "3.13": "3.13.7"})

    assert interpreter_for(SpecifierSet("<3.14.1"), FetchPythonOptions.NEVER) == "/py/3.13.7"


def test_interpreter_for_rejects_every_patch_below_a_lower_bound(mocker: MockerFixture) -> None:
    _install(mocker, {"3.13": "3.13.2"})

    with pytest.raises(PipxError, match="--fetch-python=missing"):
        interpreter_for(SpecifierSet(">=3.13.5,<3.14"), FetchPythonOptions.NEVER)


def test_interpreter_for_fetches_when_the_caller_allows_it(mocker: MockerFixture) -> None:
    _install(mocker, {}, fetched={"3.11": "3.11.9"})

    assert interpreter_for(SpecifierSet("==3.11.*"), FetchPythonOptions.MISSING) == "/downloaded/3.11.9"


def test_interpreter_for_reports_a_system_without_a_match(mocker: MockerFixture) -> None:
    _install(mocker, {})

    with pytest.raises(PipxError, match="--fetch-python=missing"):
        interpreter_for(SpecifierSet("==3.11.*"), FetchPythonOptions.NEVER)


def test_interpreter_for_reports_a_constraint_no_release_meets() -> None:
    with pytest.raises(PipxError, match="No Python that pipx supports satisfies"):
        interpreter_for(SpecifierSet("<3.5"), FetchPythonOptions.NEVER)


@pytest.fixture
def older_python(pipx_temp_env: None, monkeypatch: pytest.MonkeyPatch) -> str:
    # pipx_temp_env strips the system directories out of PATH, and pipx looks the interpreters up there
    del pipx_temp_env
    monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
    for minor in range(sys.version_info[1] - 1, int(MINIMUM_PYTHON_VERSION.split(".")[1]) - 1, -1):
        if (found := shutil.which(f"python3.{minor}")) is not None:
            return found
    pytest.skip("no supported Python older than the one running the tests")


@pytest.fixture
def make_needs_project(tmp_path: Path) -> Callable[[str], Path]:
    def create(requires_python: str) -> Path:
        project: Final[Path] = tmp_path / "needs-older"
        (project / "needs_older").mkdir(parents=True)
        (project / "needs_older" / "__init__.py").touch()
        (project / "needs_older" / "main.py").write_text("def main() -> None:\n    print('needs-older')\n")
        (project / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["flit-core"]\nbuild-backend = "flit_core.buildapi"\n\n'
            '[project]\nname = "needs-older"\nversion = "0.1"\ndescription = "Need another Python."\n'
            f'requires-python = "{requires_python}"\n'
            'scripts.needs-older = "needs_older.main:main"\n'
        )
        return project

    return create


@pytest.fixture
def project_excluding_this_python(make_needs_project: Callable[[str], Path]) -> Path:
    return make_needs_project(f"<{sys.version_info.major}.{sys.version_info.minor}")


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env", "older_python", "capsys")
def test_install_moves_to_a_python_the_package_supports(
    project_excluding_this_python: Path,
    backend: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv binary not on PATH")

    assert not run_pipx_cli(["install", "--backend", backend, str(project_excluding_this_python)])

    recorded: Final[str] = PipxMetadata(paths.ctx.venvs / "needs-older").python_version or ""
    assert recorded != f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
def test_install_uv_moves_off_a_default_python_below_the_lower_bound(
    make_needs_project: Callable[[str], Path], older_python: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", older_python)
    project: Final[Path] = make_needs_project(f">={sys.version_info.major}.{sys.version_info.minor}")

    assert not run_pipx_cli(["install", "--backend", "uv", str(project)])

    recorded: Final[str] = PipxMetadata(paths.ctx.venvs / "needs-older").python_version or ""
    assert not recorded.startswith(f"Python {older_python.rsplit('python', 1)[1]}.")


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
def test_install_json_reports_the_python_it_moved_to_on_stderr(
    make_needs_project: Callable[[str], Path],
    older_python: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    backend: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv binary not on PATH")
    monkeypatch.setenv("PIPX_DEFAULT_PYTHON", older_python)
    project: Final[Path] = make_needs_project(f">={sys.version_info.major}.{sys.version_info.minor}")

    assert not run_pipx_cli(["install", "--output", "json", "--backend", backend, str(project)])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out)["status"], "This package needs Python >=" in captured.err) == ("success", True)


@pytest.mark.usefixtures("older_python")
def test_install_moving_to_a_supported_python_reports_no_pip_error(
    project_excluding_this_python: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", str(project_excluding_this_python)])

    assert "Fatal error from pip" not in capsys.readouterr().err


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_refuses_a_named_python_the_package_rules_out(
    project_excluding_this_python: Path,
    backend: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv binary not on PATH")

    run_pipx_cli(["install", "--backend", backend, "--python", sys.executable, str(project_excluding_this_python)])

    assert "The Python you named does not satisfy" in capsys.readouterr().err
