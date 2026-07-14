from __future__ import annotations

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
    from pathlib import Path

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


def test_interpreter_for_takes_the_newest_installed_match(mocker: MockerFixture) -> None:
    find = mocker.patch("pipx.requires_python.find_python_interpreter", return_value="/usr/bin/python3.11")

    assert interpreter_for(SpecifierSet("<3.12"), FetchPythonOptions.NEVER) == "/usr/bin/python3.11"
    assert find.call_args.args[0] == "3.11"


def test_interpreter_for_skips_a_version_the_system_lacks(mocker: MockerFixture) -> None:
    def resolve(version: str, _fetch: FetchPythonOptions) -> str:
        if version == "3.11":
            raise InterpreterResolutionError(source="the system", version=version)
        return f"/usr/bin/python{version}"

    mocker.patch("pipx.requires_python.find_python_interpreter", side_effect=resolve)

    assert interpreter_for(SpecifierSet("<3.12"), FetchPythonOptions.NEVER) == "/usr/bin/python3.10"


def test_interpreter_for_fetches_when_the_caller_allows_it(mocker: MockerFixture) -> None:
    find = mocker.patch(
        "pipx.requires_python.find_python_interpreter",
        side_effect=[InterpreterResolutionError(source="the system", version="3.11"), "/downloaded/python3.11"],
    )

    assert interpreter_for(SpecifierSet("==3.11.*"), FetchPythonOptions.MISSING) == "/downloaded/python3.11"
    assert find.call_args.args[1] is FetchPythonOptions.MISSING


def test_interpreter_for_reports_a_system_without_a_match(mocker: MockerFixture) -> None:
    mocker.patch(
        "pipx.requires_python.find_python_interpreter",
        side_effect=InterpreterResolutionError(source="the system", version="3.11"),
    )

    with pytest.raises(PipxError, match="--fetch-python=missing"):
        interpreter_for(SpecifierSet("==3.11.*"), FetchPythonOptions.NEVER)


def test_interpreter_for_reports_a_constraint_no_release_meets() -> None:
    with pytest.raises(PipxError, match="No Python that pipx supports satisfies"):
        interpreter_for(SpecifierSet("<3.5"), FetchPythonOptions.NEVER)


@pytest.fixture
def older_python(pipx_temp_env: None, monkeypatch: pytest.MonkeyPatch) -> str:
    # pipx_temp_env strips the system directories out of PATH, and pipx looks the interpreters up there
    monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
    for minor in range(sys.version_info[1] - 1, int(MINIMUM_PYTHON_VERSION.split(".")[1]) - 1, -1):
        if (found := shutil.which(f"python3.{minor}")) is not None:
            return found
    pytest.skip("no supported Python older than the one running the tests")


@pytest.fixture
def project_excluding_this_python(tmp_path: Path) -> Path:
    project: Final[Path] = tmp_path / "needs-older"
    (project / "needs_older").mkdir(parents=True)
    (project / "needs_older" / "__init__.py").touch()
    (project / "needs_older" / "main.py").write_text("def main() -> None:\n    print('needs-older')\n")
    (project / "setup.py").write_text(
        "from setuptools import setup\n\n"
        "setup(\n"
        "    name='needs-older',\n"
        "    version='0.1',\n"
        "    packages=['needs_older'],\n"
        f"    python_requires='<{sys.version_info.major}.{sys.version_info.minor}',\n"
        "    entry_points={'console_scripts': ['needs-older=needs_older.main:main']},\n"
        ")\n"
    )
    return project


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
def test_install_moves_to_a_python_the_package_supports(
    pipx_temp_env: None,
    project_excluding_this_python: Path,
    older_python: str,
    capsys: pytest.CaptureFixture[str],
    backend: str,
) -> None:
    if backend == "uv" and shutil.which("uv") is None:
        pytest.skip("uv binary not on PATH")

    assert not run_pipx_cli(["install", "--backend", backend, str(project_excluding_this_python)])

    recorded: Final[str] = PipxMetadata(paths.ctx.venvs / "needs-older").python_version or ""
    assert recorded != f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
