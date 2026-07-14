from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Final

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from pipx.constants import MINIMUM_PYTHON_VERSION, FetchPythonOptions
from pipx.interpreter import InterpreterResolutionError, find_python_interpreter
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# pip prints this and installs nothing; uv installs the package regardless, so the metadata check covers that backend
_PIP_REJECTION: Final[re.Pattern[str]] = re.compile(
    r"""
    requires\ a\ different\ Python:   # pip's wording for a Requires-Python mismatch
    \s*\S+                            # the interpreter version pip rejected
    \s*not\ in\ '(?P<constraint>[^']*)'
    """,
    re.VERBOSE,
)
# the newest release pipx looks for when a package rules out the default interpreter
_NEWEST_PYTHON_MINOR: Final[int] = 14


class IncompatiblePythonError(PipxError):
    def __init__(self, constraint: SpecifierSet) -> None:
        self.constraint: Final[SpecifierSet] = constraint
        super().__init__(f"This package needs a Python matching {str(constraint)!r}.")


def rejected_constraint(backend_output: str) -> SpecifierSet | None:
    match: Final[re.Match[str] | None] = _PIP_REJECTION.search(backend_output)
    if match is None:
        return None
    return _parse(match.group("constraint"))


def unsatisfied_constraint(requires_python: str | None, python_version: str) -> SpecifierSet | None:
    """The declared constraint when ``python_version`` fails it, otherwise nothing."""
    if not requires_python or (constraint := _parse(requires_python)) is None:
        return None
    return None if constraint.contains(python_version, prereleases=True) else constraint


def interpreter_for(constraint: SpecifierSet, fetch_python: FetchPythonOptions) -> str:
    candidates: Final[list[str]] = [version for version in _candidate_versions() if constraint.contains(version)]
    if not candidates:
        raise PipxError(f"No Python that pipx supports satisfies {str(constraint)!r}.")

    for candidate in candidates:
        try:
            interpreter = find_python_interpreter(candidate, FetchPythonOptions.NEVER)
        except (InterpreterResolutionError, PipxError):
            continue
        _LOGGER.info("Python %s satisfies %s", candidate, constraint)
        return interpreter

    if fetch_python is FetchPythonOptions.NEVER:
        raise PipxError(
            f"This package needs a Python matching {str(constraint)!r} and none of the interpreters on this "
            f"system does. Install one of {', '.join(candidates)}, name it with --python, or pass "
            f"--fetch-python=missing to let pipx download it."
        )
    return find_python_interpreter(candidates[0], FetchPythonOptions.MISSING)


def _candidate_versions() -> Iterator[str]:
    lowest: Final[int] = int(MINIMUM_PYTHON_VERSION.split(".")[1])
    for minor in range(_NEWEST_PYTHON_MINOR, lowest - 1, -1):
        yield f"3.{minor}"


def _parse(requires_python: str) -> SpecifierSet | None:
    try:
        return SpecifierSet(requires_python)
    except InvalidSpecifier:
        _LOGGER.info("Cannot read the Python constraint %r", requires_python)
        return None


__all__ = [
    "interpreter_for",
    "rejected_constraint",
    "unsatisfied_constraint",
]
