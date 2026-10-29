from __future__ import annotations

import pytest

from pipx import main
from pipx.constants import FetchPythonOptions


@pytest.mark.parametrize(
    ("missing_raw", "python_raw", "expected_option", "expected_invalid"),
    [
        pytest.param(None, None, FetchPythonOptions.NEVER, False, id="unset"),
        pytest.param("1", None, FetchPythonOptions.MISSING, False, id="legacy-truthy"),
        pytest.param("0", None, FetchPythonOptions.NEVER, False, id="legacy-falsy"),
        pytest.param(" False ", None, FetchPythonOptions.NEVER, False, id="legacy-whitespace-falsy"),
        pytest.param("n", None, FetchPythonOptions.NEVER, False, id="legacy-falsy-n"),
        pytest.param(None, "always", FetchPythonOptions.ALWAYS, False, id="explicit-always"),
        pytest.param(None, "garbage", FetchPythonOptions.NEVER, True, id="invalid-value"),
    ],
)
def test_compute_fetch_python(
    missing_raw: str | None,
    python_raw: str | None,
    expected_option: FetchPythonOptions,
    expected_invalid: bool,
) -> None:
    option, invalid = main._compute_fetch_python(missing_raw, python_raw)  # ruff:ignore[private-member-access]  # parsed once at import, so per-test env changes cannot reach it
    assert option is expected_option
    assert invalid is expected_invalid


@pytest.mark.parametrize(
    ("raw", "expected_days", "expected_invalid"),
    [
        pytest.param(None, None, False, id="unset"),
        pytest.param("  ", None, False, id="blank"),
        pytest.param("7", 7, False, id="days"),
        pytest.param(" 7 ", 7, False, id="whitespace-padded"),
        pytest.param("0", 0, False, id="zero"),
        pytest.param("-1", None, True, id="negative"),
        pytest.param("garbage", None, True, id="not-an-integer"),
    ],
)
def test_compute_cooldown(raw: str | None, expected_days: int | None, expected_invalid: bool) -> None:
    assert main._compute_cooldown(raw) == (expected_days, expected_invalid)  # ruff:ignore[private-member-access]  # parsed once at import, so per-test env changes cannot reach it


@pytest.mark.parametrize(
    ("raw", "expected_logs", "expected_invalid"),
    [
        pytest.param(None, 10, False, id="unset"),
        pytest.param("", 10, False, id="empty"),
        pytest.param("   ", 10, False, id="whitespace-only"),
        pytest.param("10", 10, False, id="default"),
        pytest.param(" 5 ", 5, False, id="whitespace-padded"),
        pytest.param("0", 0, False, id="zero"),
        pytest.param("-1", 10, True, id="negative"),
        pytest.param("garbage", 10, True, id="not-an-integer"),
    ],
)
def test_compute_max_logs(raw: str | None, expected_logs: int, expected_invalid: bool) -> None:
    assert main._compute_max_logs(raw) == (expected_logs, expected_invalid)  # ruff:ignore[private-member-access]  # parsed once at import, so per-test env changes cannot reach it
