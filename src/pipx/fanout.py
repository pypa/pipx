from __future__ import annotations

__lazy_modules__ = ["concurrent.futures", "functools", "signal"]

import logging
import os
import signal
import sys
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import contextmanager, suppress
from contextvars import Context, ContextVar, copy_context
from dataclasses import dataclass, field
from functools import partial
from threading import Condition, Event, RLock, current_thread, main_thread
from typing import TYPE_CHECKING, Final, NoReturn, TextIO, TypeVar, cast

from pipx.constants import WINDOWS

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from subprocess import Popen
    from types import FrameType

    from filelock import BaseFileLock

    _Child = Popen[str] | Popen[bytes]

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_ResultT = TypeVar("_ResultT")
_SLOT: Final[ContextVar[_Slot | None]] = ContextVar("fanout_slot", default=None)
# the children started outside a fan-out, which a signal handler stops, hence reentrant
_LOOSE_CHILDREN: Final[set[_Child]] = set()
_LOOSE_CHILDREN_LOCK: Final[RLock] = RLock()


@contextmanager
def stopping_children_on_signals() -> Generator[Event, None, None]:
    """Turn SIGINT, SIGTERM and SIGHUP into KeyboardInterrupt, stopping the children started outside a fan-out first.

    Children run in a process group of their own, so a Ctrl-C in the terminal reaches pipx alone and pipx stops them.
    Once signalled, pipx is about to exit, so it ignores further signals from then on: one landing while it exits would
    end it with a traceback instead of its exit code. Yields an event set once a signal arrived.
    """
    signalled: Final[Event] = Event()
    if current_thread() is not main_thread():
        yield signalled
        return

    def interrupt(_number: int, _frame: FrameType | None) -> NoReturn:
        signalled.set()
        with _LOOSE_CHILDREN_LOCK:
            for process in _LOOSE_CHILDREN:
                stop_process_group(process)
        raise KeyboardInterrupt

    # Windows has no SIGHUP
    previous: Final = {
        number: signal.signal(number, interrupt)
        for number in {signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGHUP", signal.SIGTERM)}
    }
    try:
        yield signalled
    finally:
        for number, handler in previous.items():
            signal.signal(number, signal.SIG_IGN if signalled.is_set() else handler)


def fan_out(
    tasks: Sequence[Callable[[], _ResultT]],
    *,
    sequential: bool,
    interrupted: Callable[[int], _ResultT] | None = None,
) -> list[_ResultT]:
    """Run the tasks concurrently, printing what each one writes in task order, as if they ran one after another.

    The earliest unfinished task writes to the terminal directly; the others buffer until it is their turn. When a task
    raises, tasks that have not started yet are cancelled and the first exception, in task order, propagates.

    An interrupt stops the children of every task and propagates once the tasks have rolled back. With ``interrupted``,
    the first interrupt instead lets the work tasks run under :func:`finished_on_interrupt` finish, a second one stops
    that too, and each task cut short or never started returns ``interrupted(its index)``.
    """
    if sequential or not tasks:
        return [task() for task in tasks]
    # capped like the outdated check, so a large pipx home does not start dozens of pip or uv runs against the index
    workers: Final[int] = min(len(tasks), os.cpu_count() or 1, 8)
    turn: Final[Condition] = Condition()
    # the turn's lock also guards the children, which no task holds while waiting for a child to exit
    children: Final[_Children] = _Children(turn, Event(), finishes=interrupted is not None)
    slots: Final[list[_Slot]] = []
    for _ in tasks:
        slots.append(_Slot(turn, children, live=not slots, after=slots[-1] if slots else None))
    executor: Final[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=workers)
    with _routed_output(children):
        futures: Final[list[Future[_ResultT]]] = []
        try:
            futures.extend(
                executor.submit(_in_slot(slot, partial(_once_submitted, slot, task)))
                for slot, task in zip(slots, tasks, strict=True)
            )
            children.submitted.set()
            _wait_in_order(futures, slots)
        except KeyboardInterrupt:
            _interrupt(futures, children)
            if interrupted is None:
                raise
            if not children.interrupted:
                _finish_in_order(futures, slots, children)
        finally:
            children.submitted.set()
            _settle(futures, slots, children)
            executor.shutdown(cancel_futures=True)
    if interrupted is None or not children.stopping:
        return [future.result() for future in futures]
    return [
        interrupted(index)
        if future.cancelled() or isinstance(future.exception(), KeyboardInterrupt)
        else future.result()
        for index, future in enumerate(futures)
    ]


def _wait_in_order(futures: list[Future[_ResultT]], slots: list[_Slot]) -> None:
    for future, next_slot in zip(futures, slots[1:], strict=False):
        _wait_interruptibly((future,))
        if not future.cancelled() and future.exception() is not None:
            for later in futures:
                later.cancel()
        next_slot.go_live()
    # the loop stops short of the last task, which shutdown would cancel if no thread has picked it up yet
    _wait_interruptibly(futures)


def _wait_interruptibly(futures: Sequence[Future[_ResultT]]) -> None:
    # a blocked wait does not wake for a signal another thread handled or one that landed just before it blocked, so
    # wait in slices for the interpreter to run the handler and raise KeyboardInterrupt promptly
    while wait(futures, timeout=0.1).not_done:
        pass


def _interrupt(futures: list[Future[_ResultT]], children: _Children) -> None:
    # the children run in process groups of their own, out of reach of the terminal's Ctrl-C, so pipx stops them itself
    for future in futures:
        future.cancel()
    if finishing := children.stop():
        _LOGGER.warning(
            "Finishing the %d environment(s) already being changed; press Ctrl-C again to stop them too.", finishing
        )


def _finish_in_order(futures: list[Future[_ResultT]], slots: list[_Slot], children: _Children) -> None:
    # the tasks left to finish keep printing in task order, unless interrupted again
    try:
        _wait_in_order(futures, slots)
    except KeyboardInterrupt:
        _interrupt(futures, children)


def _settle(futures: list[Future[_ResultT]], slots: list[_Slot], children: _Children) -> None:
    # a further Ctrl-C must not cut short the wait for tasks rolling back: Python 3.12 marks a thread whose join was
    # interrupted as stopped, so the interpreter exits without waiting and kills the task mid rollback
    while True:
        try:
            # an interrupt can leave tasks waiting for their turn, so hand every slot over before waiting on them
            for slot in slots:
                slot.go_live()
            _wait_interruptibly(futures)
        except KeyboardInterrupt:
            _interrupt(futures, children)
        else:
            return


def output_is_held() -> bool:
    """Whether output written now is buffered until the earlier tasks of a fan-out have finished."""
    return (slot := _SLOT.get()) is not None and not slot.live


@contextmanager
def in_turn(done: Callable[[], bool]) -> Generator[None, None, None]:
    """Change state shared by all tasks of a fan-out only once the earlier tasks have finished, unless done() is true.

    Running sequentially, the first task to need the change makes it and the later ones find it made; waiting for the
    turn keeps that task, its arguments and its output the same when running concurrently.
    """
    if (slot := _SLOT.get()) is None:
        yield
        return
    with slot.turn:
        slot.turn.wait_for(lambda: slot.live or done())
    try:
        yield
    finally:
        with slot.turn:
            slot.turn.notify_all()


@contextmanager
def locked_in_order(lock: BaseFileLock) -> Generator[BaseFileLock, None, None]:
    """Take the lock only once the earlier tasks of a fan-out have taken theirs or finished.

    A task waiting for its turn holds its lock, so two pipx runs taking the same locks in different task orders could
    each wait for the other forever; taking them in task order leaves no task waiting its turn on a lock another run
    holds while it waits for this run.
    """
    if (slot := _SLOT.get()) is not None:
        with slot.turn:
            slot.turn.wait_for(lambda: slot.live or slot.after is None or slot.after.locked)
    with lock:
        if slot is not None:
            slot.pass_lock()
        yield lock


@contextmanager
def finished_on_interrupt() -> Generator[None, None, None]:
    """Let the work in this block finish when a fan-out that takes ``interrupted`` is interrupted for the first time.

    Raises KeyboardInterrupt instead of starting the work once that fan-out is interrupted.
    """
    if (slot := _SLOT.get()) is None or not slot.children.finishes:
        yield
        return
    children: Final[_Children] = slot.children
    with children.lock:
        if children.stopping:
            raise KeyboardInterrupt
        children.finishing.add(slot)
    try:
        yield
    finally:
        with children.lock:
            children.finishing.discard(slot)


@contextmanager
def stopped_on_interrupt(process: _Child) -> Generator[None, None, None]:
    """Stop the child process when pipx is interrupted, interrupting the fan-out task that runs it too.

    The child must run in a process group of its own, which stopping it ends as a whole.
    """
    if (slot := _SLOT.get()) is None:
        with _LOOSE_CHILDREN_LOCK:
            _LOOSE_CHILDREN.add(process)
        try:
            yield
        finally:
            with _LOOSE_CHILDREN_LOCK:
                _LOOSE_CHILDREN.discard(process)
        return
    children: Final[_Children] = slot.children
    with children.lock:
        children.running[process] = slot
        if children.stops(slot):
            stop_process_group(process)
    try:
        yield
    finally:
        with children.lock:
            del children.running[process]
    if children.stops(slot):
        raise KeyboardInterrupt


def stop_process_group(process: _Child) -> None:
    """Stop a child started in a process group of its own, together with everything it started."""
    if WINDOWS:
        process.terminate()
        return
    # the group outlives its leader while a grandchild such as a build backend still runs; an empty group raises
    # ProcessLookupError, and macOS raises PermissionError for one holding only zombies
    with suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGTERM)


@dataclass
class _Children:
    lock: Condition
    submitted: Event
    finishes: bool
    running: dict[_Child, _Slot] = field(default_factory=dict)
    finishing: set[_Slot] = field(default_factory=set)
    stopping: bool = False
    interrupted: bool = False
    # the writer that left each stream's last line open
    open_lines: dict[TextIO, object] = field(default_factory=dict)

    def stop(self) -> int:
        """Stop the children of the tasks not finishing their work, or of every task when there is none or once more.

        Returns how many tasks finish their work.
        """
        with self.lock:
            if self.stopping or not self.finishing:
                self.interrupted = True
                # a line a stopped child left open stays unfinished, so whatever comes next starts a line of its own
                self.open_lines = dict.fromkeys(self.open_lines, object())
            self.stopping = True
            for process, slot in self.running.items():
                if self.stops(slot):
                    stop_process_group(process)
            return 0 if self.interrupted else len(self.finishing)

    def stops(self, slot: _Slot) -> bool:
        return self.interrupted or (self.stopping and slot not in self.finishing)

    def write(self, target: TextIO, text: str, writer: object) -> int:
        with self.lock:
            # once interrupted, tasks write out of turn and must not run on into a line another one left unfinished
            if self.interrupted and self.open_lines.get(target, writer) is not writer and text[:1] not in {"\n", "\r"}:
                target.write("\n")
            if text.endswith("\n"):
                self.open_lines.pop(target, None)
            elif text:
                self.open_lines[target] = writer
            return target.write(text)


@dataclass(eq=False)
class _Slot:
    turn: Condition
    children: _Children
    live: bool
    after: _Slot | None
    locked: bool = False
    chunks: list[tuple[TextIO, str]] = field(default_factory=list)

    def pass_lock(self) -> None:
        with self.turn:
            self.locked = True
            self.turn.notify_all()

    def go_live(self) -> None:
        with self.turn:
            for stream, text in self.chunks:
                self.children.write(stream, text, self)
                stream.flush()
            self.chunks.clear()
            self.live = True
            self.turn.notify_all()


def _in_slot(slot: _Slot, task: Callable[[], _ResultT]) -> Callable[[], _ResultT]:
    # executor threads do not inherit the submitter's context, which carries pipx's switches as well as the slot
    context: Final[Context] = copy_context()
    context.run(_SLOT.set, slot)
    return partial(context.run, task)


def _once_submitted(slot: _Slot, task: Callable[[], _ResultT]) -> _ResultT:
    # an interrupt landing while submit starts a worker thread leaves that thread out of the threads shutdown waits on,
    # so no task may start its work before every task is submitted, and none once the fan-out is interrupted
    try:
        slot.children.submitted.wait()
        if slot.children.stopping:
            raise KeyboardInterrupt
        return task()
    finally:
        # a task that ends without taking a lock must not hold back the later tasks waiting to take theirs
        slot.pass_lock()


@contextmanager
def _routed_output(children: _Children) -> Generator[None, None, None]:
    stdout, stderr = sys.stdout, sys.stderr
    # the stream handler bound sys.stderr when logging was set up, so it does not see the replacement below
    handlers: Final[list[tuple[logging.StreamHandler[TextIO], TextIO]]] = [
        (handler, handler.stream)
        for handler in logging.getLogger("pipx").handlers
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
    ]
    sys.stdout, sys.stderr = _routed(stdout, children), _routed(stderr, children)
    for handler, stream in handlers:
        handler.setStream(_routed(stream, children))
    try:
        yield
    finally:
        sys.stdout, sys.stderr = stdout, stderr
        for handler, stream in handlers:
            handler.setStream(stream)


def _routed(target: TextIO, children: _Children) -> TextIO:
    # a duck-typed stand-in rather than an io.TextIOBase subclass, whose finalizer would flush a target closed by then
    return cast("TextIO", _RoutedStream(target, children))


class _RoutedStream:
    def __init__(self, target: TextIO, children: _Children) -> None:
        self._target: Final[TextIO] = target
        self._children: Final[_Children] = children

    def __getattr__(self, name: str) -> object:
        return getattr(self._target, name)

    def write(self, text: str) -> int:
        slot: Final[_Slot | None] = _SLOT.get()
        with self._children.lock:
            if slot is None or slot.live:
                return self._children.write(self._target, text, slot)
            slot.chunks.append((self._target, text))
        return len(text)

    def flush(self) -> None:
        if (slot := _SLOT.get()) is None or slot.live:
            self._target.flush()


__all__ = [
    "fan_out",
    "finished_on_interrupt",
    "in_turn",
    "locked_in_order",
    "output_is_held",
    "stop_process_group",
    "stopped_on_interrupt",
    "stopping_children_on_signals",
]
