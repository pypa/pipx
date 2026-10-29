from __future__ import annotations

import pytest

from pipx import constants


@pytest.mark.parametrize(
    ("missing_raw", "python_raw", "expected_option", "expected_invalid"),
    [
        pytest.param(None, None, constants.FetchPythonOptions.NEVER, False, id="unset"),
        pytest.param("1", None, constants.FetchPythonOptions.MISSING, False, id="legacy-truthy"),
        pytest.param("0", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy"),
        pytest.param(" False ", None, constants.FetchPythonOptions.NEVER, False, id="legacy-whitespace-falsy"),
        pytest.param("n", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy-n"),
        pytest.param(None, "always", constants.FetchPythonOptions.ALWAYS, False, id="explicit-always"),
        pytest.param(None, "garbage", constants.FetchPythonOptions.NEVER, True, id="invalid-value"),
    ],
)
def test_compute_fetch_python(
    missing_raw: str | None,
    python_raw: str | None,
    expected_option: constants.FetchPythonOptions,
    expected_invalid: bool,
) -> None:
    option, invalid = constants.compute_fetch_python(missing_raw, python_raw)
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
    assert constants.compute_cooldown(raw) == (expected_days, expected_invalid)


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
    assert constants.compute_max_logs(raw) == (expected_logs, expected_invalid)
