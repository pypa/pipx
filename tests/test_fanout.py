from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from typing import TYPE_CHECKING, Final

import pytest
from filelock import FileLock, Timeout

from helpers import skip_if_windows
from pipx.fanout import (
    fan_out,
    finished_on_interrupt,
    in_turn,
    locked_in_order,
    output_is_held,
    stopping_children_on_signals,
)
from pipx.util import run_subprocess

if TYPE_CHECKING:
    from pathlib import Path


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


@skip_if_windows
def test_fan_out_waits_for_rollback_through_second_interrupt() -> None:
    rolled_back: Final[list[str]] = []
    main_thread: Final[int] = threading.get_ident()

    def rolling_back() -> None:
        for _ in range(2):
            signal.pthread_kill(main_thread, signal.SIGINT)
            time.sleep(0.2)
        rolled_back.append("first")

    with pytest.raises(KeyboardInterrupt):
        fan_out([rolling_back, int], sequential=False)

    assert rolled_back == ["first"]


@skip_if_windows
def test_fan_out_interrupted_by_signal_another_thread_handles() -> None:
    def interrupted() -> None:
        # a signal sent to the whole process can land on any thread; the interpreter runs its handler on the main thread
        signal.pthread_kill(threading.get_ident(), signal.SIGINT)
        run_subprocess([sys.executable, "-c", "import time; time.sleep(30)"])

    with pytest.raises(KeyboardInterrupt):
        fan_out([interrupted, int], sequential=False)


def test_locked_in_order_leaves_no_lock_cycle_with_another_run(tmp_path: Path) -> None:
    first_lock: Final[Path] = tmp_path / "first.lock"
    second_lock: Final[Path] = tmp_path / "second.lock"
    other_run_holds_first: Final[threading.Event] = threading.Event()
    second_task_locked: Final[threading.Event] = threading.Event()
    other_run: Final[list[str]] = []

    def take_locks_in_reverse() -> None:
        with FileLock(first_lock):
            other_run_holds_first.set()
            second_task_locked.wait(timeout=0.5)
            try:
                with FileLock(second_lock, timeout=2):
                    other_run.append("took both")
            except Timeout:
                other_run.append("deadlocked")

    def first() -> bool:
        with locked_in_order(FileLock(first_lock)) as lock:
            return lock.is_locked

    def second() -> str:
        with locked_in_order(FileLock(second_lock)):
            second_task_locked.set()
            with in_turn(lambda: False):
                return "in turn"

    thread: Final[threading.Thread] = threading.Thread(target=take_locks_in_reverse)
    thread.start()
    other_run_holds_first.wait(timeout=5)
    fan_out([first, second], sequential=False)
    thread.join()

    assert other_run == ["took both"]


@skip_if_windows
@pytest.mark.usefixtures("signal_handlers")
def test_fan_out_stops_children_on_sigterm() -> None:
    def terminated() -> None:
        run_subprocess([
            sys.executable,
            "-c",
            "import os, signal, time; os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)",
        ])

    with pytest.raises(KeyboardInterrupt), stopping_children_on_signals():
        fan_out([terminated, int], sequential=False)


@skip_if_windows
@pytest.mark.usefixtures("signal_handlers")
def test_signal_stops_the_grandchildren_of_a_child(tmp_path: Path) -> None:
    pid_file: Final[Path] = tmp_path / "grandchild.pid"
    # the grandchild stands in for a build backend that pip or uv started
    script: Final[str] = (
        "import os, signal, subprocess, sys, time; "
        "grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"open({str(pid_file)!r}, 'w').write(str(grandchild.pid)); "
        "os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"
    )

    with pytest.raises(KeyboardInterrupt), stopping_children_on_signals():
        run_subprocess([sys.executable, "-c", script])

    assert _exits_within(int(pid_file.read_text()), seconds=5)


def _exits_within(pid: int, *, seconds: float) -> bool:
    deadline: Final[float] = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


@pytest.mark.usefixtures("signal_handlers")
def test_signals_keep_their_handlers_after_an_unsignalled_block() -> None:
    previous: Final = signal.getsignal(signal.SIGTERM)

    with stopping_children_on_signals():
        pass

    assert signal.getsignal(signal.SIGTERM) is previous


def test_signals_keep_their_handlers_off_the_main_thread() -> None:
    signalled: Final[list[bool]] = []

    def run() -> None:
        with stopping_children_on_signals() as event:
            signalled.append(event.is_set())

    thread: Final[threading.Thread] = threading.Thread(target=run)
    thread.start()
    thread.join()

    assert signalled == [False]


@skip_if_windows
@pytest.mark.usefixtures("signal_handlers")
def test_signals_are_ignored_once_signalled() -> None:
    with pytest.raises(KeyboardInterrupt), stopping_children_on_signals():
        signal.raise_signal(signal.SIGINT)

    assert signal.getsignal(signal.SIGINT) is signal.SIG_IGN


@skip_if_windows
@pytest.mark.usefixtures("signal_handlers")
def test_fan_out_finishes_started_work_after_first_interrupt(caplog: pytest.LogCaptureFixture) -> None:
    main_thread: Final[int] = threading.get_ident()

    def finishing() -> str:
        with finished_on_interrupt():
            signal.pthread_kill(main_thread, signal.SIGINT)
            _wait_for_log(caplog, "Finishing the 1 environment(s)")
            run_subprocess([sys.executable, "-c", "pass"])
        return "finished"

    def not_started() -> str:
        _wait_for_log(caplog, "Finishing the 1 environment(s)")
        with finished_on_interrupt():
            return "started"

    assert fan_out([finishing, not_started], sequential=False, interrupted=lambda index: f"interrupted {index}") == [
        "finished",
        "interrupted 1",
    ]


@skip_if_windows
@pytest.mark.usefixtures("signal_handlers")
def test_fan_out_stops_started_work_on_second_interrupt(caplog: pytest.LogCaptureFixture) -> None:
    main_thread: Final[int] = threading.get_ident()

    def finishing() -> str:
        with finished_on_interrupt():
            signal.pthread_kill(main_thread, signal.SIGINT)
            _wait_for_log(caplog, "Finishing the 1 environment(s)")
            signal.pthread_kill(main_thread, signal.SIGINT)
            run_subprocess([sys.executable, "-c", "import time; time.sleep(30)"])
        return "finished"

    assert fan_out([finishing], sequential=False, interrupted=lambda index: f"interrupted {index}") == ["interrupted 0"]


def _wait_for_log(caplog: pytest.LogCaptureFixture, text: str) -> None:
    deadline: Final[float] = time.monotonic() + 5
    while not any(text in message for message in caplog.messages) and time.monotonic() < deadline:
        time.sleep(0.01)


def test_fan_out_runs_off_the_main_thread() -> None:
    results: Final[list[list[int]]] = []
    thread: Final[threading.Thread] = threading.Thread(
        target=lambda: results.append(fan_out([int, int], sequential=False))
    )
    thread.start()
    thread.join()

    assert results == [[0, 0]]


@skip_if_windows
def test_fan_out_interrupted_ends_unfinished_line_before_held_output(
    capsys: pytest.CaptureFixture[str], second_done: threading.Event
) -> None:
    main_thread: Final[int] = threading.get_ident()

    def interrupted() -> None:
        second_done.wait(timeout=5)
        sys.stderr.write("building first -")
        signal.pthread_kill(main_thread, signal.SIGINT)
        run_subprocess([sys.executable, "-c", "import time; time.sleep(30)"])

    def held() -> None:
        sys.stderr.write("installing second\n")
        second_done.set()

    with pytest.raises(KeyboardInterrupt):
        fan_out([interrupted, held], sequential=False)

    assert capsys.readouterr().err == "building first -\ninstalling second\n"
