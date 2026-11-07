from __future__ import annotations

__lazy_modules__ = ["packaging.specifiers", "pipx.interpreter", "pipx.subprocess_runner", "re"]

import logging
import re
from typing import TYPE_CHECKING, Final

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from pipx.constants import MINIMUM_PYTHON_VERSION, FetchPythonOptions
from pipx.interpreter import InterpreterResolutionError, find_python_interpreter
from pipx.subprocess_runner import run_subprocess
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# the newest release pipx looks for when a package rules out the default interpreter
_NEWEST_PYTHON_MINOR: Final[int] = 15


class IncompatiblePythonError(PipxError):
    def __init__(self, constraint: SpecifierSet) -> None:
        self.constraint: Final[SpecifierSet] = constraint
        super().__init__(f"This package needs a Python matching {str(constraint)!r}.")


def rejected_constraint(backend_output: str) -> SpecifierSet | None:
    # pip and uv print these and install nothing; uv only checks lower bounds, so the metadata check covers the rest
    match: Final[re.Match[str] | None] = re.search(
        r"""
        requires\ a\ different\ Python:\s*\S+\s*not\ in\ '(?P<pip>[^']*)'
        | current\s+Python\s+version\s+\(\S+\)\s+does\s+not\s+satisfy\s+Python(?P<uv>\S+?),?(?=\s|$)
        | current\s+Python\s+version\s+\(\S+\)\s+does\s+not\s+satisfy\s+all\s+of:\n
          (?P<uv_union>(?:[ \t]*Python\S+[ \t]*\n?)+)
        """,
        backend_output,
        re.VERBOSE,
    )
    if match is None:
        return None
    if match["uv_union"] is None:
        return _parse(match["pip"] or match["uv"])
    # uv splits a constraint with an exclusion, such as >=3.12,!=3.15.*, into ranges any of which will do; a set of
    # specifiers cannot express that union, so pipx takes the range that holds the newest Python it would pick anyway
    ranges: Final[list[SpecifierSet]] = [
        constraint for text in re.findall(r"Python(\S+)", match["uv_union"]) if (constraint := _parse(text)) is not None
    ]
    return next(
        (constraint for minor in _candidate_versions() for constraint in ranges if _minor_overlaps(constraint, minor)),
        next(iter(ranges), None),
    )


def _parse(requires_python: str) -> SpecifierSet | None:
    try:
        return SpecifierSet(requires_python)
    except InvalidSpecifier:
        _LOGGER.info("Cannot read the Python constraint %r", requires_python)
        return None


def _candidate_versions() -> Iterator[str]:
    return (f"3.{minor}" for minor in range(_NEWEST_PYTHON_MINOR, int(MINIMUM_PYTHON_VERSION.split(".")[1]) - 1, -1))


def _minor_overlaps(constraint: SpecifierSet, minor: str) -> bool:
    # no CPython minor has reached 40 patch releases, so the scan misses none
    return any(constraint.contains(f"{minor}.{patch}", prereleases=True) for patch in range(40))


def unsatisfied_constraint(requires_python: str | None, python_version: str) -> SpecifierSet | None:
    if not requires_python or (constraint := _parse(requires_python)) is None:
        return None
    return None if constraint.contains(python_version, prereleases=True) else constraint


def unsatisfied_by_interpreter(requires_python: str | None, interpreter: str) -> SpecifierSet | None:
    # an interpreter whose version pipx cannot read passes
    if (version := _interpreter_version(interpreter)) is None:
        return None
    return unsatisfied_constraint(requires_python, version)


def _interpreter_version(interpreter: str) -> str | None:
    process: Final = run_subprocess(
        [interpreter, "-c", "import sys; print('.'.join(str(part) for part in sys.version_info[:3]))"],
        capture_stderr=False,
        log_stdout=False,
    )
    return process.stdout.strip() or None if process.returncode == 0 else None


def interpreter_for(constraint: SpecifierSet, fetch_python: FetchPythonOptions) -> str:
    overlapping: Final[list[str]] = [minor for minor in _candidate_versions() if _minor_overlaps(constraint, minor)]
    if not overlapping:
        msg = f"No Python that pipx supports satisfies {str(constraint)!r}."
        raise PipxError(msg)

    for minor in overlapping:
        if (interpreter := _matching_interpreter(minor, constraint, FetchPythonOptions.NEVER)) is not None:
            return interpreter

    if fetch_python is FetchPythonOptions.NEVER:
        msg = (
            f"This package needs a Python matching {str(constraint)!r} and none of the interpreters on this "
            f"system does. Install one of {', '.join(overlapping)}, name it with --python, or pass "
            f"--fetch-python=missing to let pipx download it."
        )
        raise PipxError(msg)
    for minor in overlapping:
        if (interpreter := _matching_interpreter(minor, constraint, FetchPythonOptions.MISSING)) is not None:
            return interpreter
    msg = f"pipx could not obtain a Python matching {str(constraint)!r}."
    raise PipxError(msg)


def _matching_interpreter(minor: str, constraint: SpecifierSet, fetch_python: FetchPythonOptions) -> str | None:
    try:
        interpreter: Final[str] = find_python_interpreter(minor, fetch_python)
    except (InterpreterResolutionError, PipxError):
        return None
    # the resolved interpreter is some patch release of the minor, so pipx checks the constraint against its own version
    if (version := _interpreter_version(interpreter)) is not None and constraint.contains(version, prereleases=True):
        _LOGGER.info("Python %s satisfies %s", version, constraint)
        return interpreter
    return None


__all__ = [
    "interpreter_for",
    "rejected_constraint",
    "unsatisfied_by_interpreter",
    "unsatisfied_constraint",
]
