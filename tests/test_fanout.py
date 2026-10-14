from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Final

import pytest

from pipx.fanout import fan_out, in_turn, output_is_held


@pytest.fixture
def second_done() -> threading.Event:
    return threading.Event()


def test_fan_out_returns_results_in_task_order() -> None:
    def first() -> str:
        time.sleep(0.1)
        return "first"

    assert fan_out([first, lambda: "second"], sequential=False) == ["first", "second"]


def test_fan_out_sequential_runs_tasks_in_calling_thread() -> None:
    assert fan_out([threading.get_ident, threading.get_ident], sequential=True) == [threading.get_ident()] * 2


def test_fan_out_prints_in_task_order(capsys: pytest.CaptureFixture[str], second_done: threading.Event) -> None:
    def first() -> None:
        second_done.wait(timeout=5)
        print("first")  # ruff:ignore[print]  # the output under test

    def second() -> None:
        print("second")  # ruff:ignore[print]  # the output under test
        second_done.set()

    fan_out([first, second], sequential=False)

    assert capsys.readouterr().out == "first\nsecond\n"


def test_fan_out_logs_in_task_order(capsys: pytest.CaptureFixture[str], second_done: threading.Event) -> None:
    logging.getLogger("pipx").addHandler(logging.StreamHandler(sys.stderr))
    logger: Final[logging.Logger] = logging.getLogger("pipx.test")

    def first() -> None:
        second_done.wait(timeout=5)
        logger.warning("first")

    def second() -> None:
        logger.warning("second")
        second_done.set()

    fan_out([first, second], sequential=False)

    assert capsys.readouterr().err == "first\nsecond\n"


def test_fan_out_streams_report_the_terminal_of_the_real_stream() -> None:
    expected: Final[bool] = sys.stdout.isatty()

    assert fan_out([sys.stdout.isatty, sys.stdout.isatty], sequential=False) == [expected, expected]


def test_fan_out_finishes_last_task_queued_after_the_others() -> None:
    assert fan_out([int, int], sequential=False) == [0, 0]


def test_fan_out_raises_first_failure_in_task_order() -> None:
    def first() -> None:
        time.sleep(0.1)
        msg = "first"
        raise ValueError(msg)

    def second() -> None:
        msg = "second"
        raise ValueError(msg)

    with pytest.raises(ValueError, match=r"^first$"):
        fan_out([first, second], sequential=False)


def test_output_is_held_only_for_task_waiting_its_turn(second_done: threading.Event) -> None:
    def first() -> bool:
        second_done.wait(timeout=5)
        return output_is_held()

    def second() -> bool:
        held = output_is_held()
        second_done.set()
        return held

    assert fan_out([first, second], sequential=False) == [False, True]


def test_in_turn_waits_for_earlier_tasks() -> None:
    events: Final[list[str]] = []

    def first() -> None:
        time.sleep(0.1)
        events.append("first")

    def second() -> None:
        with in_turn(lambda: False):
            events.append("second")

    fan_out([first, second], sequential=False)

    assert events == ["first", "second"]


def test_in_turn_proceeds_once_done(second_done: threading.Event) -> None:
    def second() -> None:
        with in_turn(lambda: True):
            second_done.set()

    assert fan_out([lambda: second_done.wait(timeout=5), second], sequential=False) == [True, None]


def test_in_turn_outside_fan_out_runs_immediately() -> None:
    events: Final[list[str]] = []

    with in_turn(lambda: False):
        events.append("ran")

    assert events == ["ran"]
