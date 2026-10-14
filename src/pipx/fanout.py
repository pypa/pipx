from __future__ import annotations

__lazy_modules__ = ["concurrent.futures", "functools", "logging", "threading"]

import logging
import os
import sys
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from contextvars import Context, ContextVar, copy_context
from dataclasses import dataclass, field
from functools import partial
from threading import Condition, Event
from typing import TYPE_CHECKING, Final, TextIO, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from subprocess import Popen

    _Child = Popen[str] | Popen[bytes]

_ResultT = TypeVar("_ResultT")
_SLOT: Final[ContextVar[_Slot | None]] = ContextVar("fanout_slot", default=None)


def fan_out(tasks: Sequence[Callable[[], _ResultT]], *, sequential: bool) -> list[_ResultT]:
    """Run the tasks concurrently, printing what each one writes in task order, as if they ran one after another.

    The earliest unfinished task writes to the terminal directly; the others buffer until it is their turn. When a task
    raises, tasks that have not started yet are cancelled and the first exception, in task order, propagates.
    """
    # capped like the outdated check, so a large pipx home does not start dozens of pip or uv runs against the index
    if sequential or (workers := min(len(tasks), os.cpu_count() or 1, 8)) <= 1:
        return [task() for task in tasks]
    turn: Final[Condition] = Condition()
    # the turn's lock also guards the children, which no task holds while waiting for a child to exit
    children: Final[_Children] = _Children(turn, Event())
    slots: Final[list[_Slot]] = [_Slot(turn, children, live=index == 0) for index in range(len(tasks))]
    executor: Final[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=workers)
    with _routed_output():
        futures: Final[list[Future[_ResultT]]] = []
        try:
            futures.extend(
                executor.submit(_in_slot(slot, partial(_once_submitted, children, task)))
                for slot, task in zip(slots, tasks, strict=True)
            )
            children.submitted.set()
            _wait_in_order(futures, slots)
        except KeyboardInterrupt:
            # a SIGINT sent to pipx alone, not to its process group, leaves the children running, so stop them for the
            # running tasks to roll back now instead of finishing their work first
            for future in futures:
                future.cancel()
            children.stop()
            raise
        finally:
            children.submitted.set()
            # an interrupt can leave tasks waiting for their turn, so hand every slot over before waiting on them
            for slot in slots:
                slot.go_live()
            executor.shutdown(cancel_futures=True)
    return [future.result() for future in futures]


def _wait_in_order(futures: list[Future[_ResultT]], slots: list[_Slot]) -> None:
    for future, next_slot in zip(futures, slots[1:], strict=False):
        wait((future,))
        if not future.cancelled() and future.exception() is not None:
            for later in futures:
                later.cancel()
        next_slot.go_live()
    # the loop stops short of the last task, which shutdown would cancel if no thread has picked it up yet
    wait(futures)


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
def stopped_on_interrupt(process: _Child) -> Generator[None, None, None]:
    """Terminate the child process when the fan-out running this task is interrupted, then interrupt the task too."""
    if (slot := _SLOT.get()) is None:
        yield
        return
    children: Final[_Children] = slot.children
    with children.lock:
        children.running.add(process)
        if children.interrupted:
            process.terminate()
    try:
        yield
    finally:
        with children.lock:
            children.running.discard(process)
    if children.interrupted:
        raise KeyboardInterrupt


@dataclass
class _Children:
    lock: Condition
    submitted: Event
    running: set[_Child] = field(default_factory=set)
    interrupted: bool = False

    def stop(self) -> None:
        with self.lock:
            self.interrupted = True
            for process in self.running:
                process.terminate()


@dataclass
class _Slot:
    turn: Condition
    children: _Children
    live: bool
    chunks: list[tuple[TextIO, str]] = field(default_factory=list)

    def go_live(self) -> None:
        with self.turn:
            for stream, text in self.chunks:
                stream.write(text)
                stream.flush()
            self.chunks.clear()
            self.live = True
            self.turn.notify_all()


def _in_slot(slot: _Slot, task: Callable[[], _ResultT]) -> Callable[[], _ResultT]:
    # executor threads do not inherit the submitter's context, which carries pipx's switches as well as the slot
    context: Final[Context] = copy_context()
    context.run(_SLOT.set, slot)
    return partial(context.run, task)


def _once_submitted(children: _Children, task: Callable[[], _ResultT]) -> _ResultT:
    # an interrupt landing while submit starts a worker thread leaves that thread out of the threads shutdown waits on,
    # so no task may start its work before every task is submitted, and none once the fan-out is interrupted
    children.submitted.wait()
    if children.interrupted:
        raise KeyboardInterrupt
    return task()


@contextmanager
def _routed_output() -> Generator[None, None, None]:
    stdout, stderr = sys.stdout, sys.stderr
    # the stream handler bound sys.stderr when logging was set up, so it does not see the replacement below
    handlers: Final[list[tuple[logging.StreamHandler[TextIO], TextIO]]] = [
        (handler, handler.stream)
        for handler in logging.getLogger("pipx").handlers
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
    ]
    sys.stdout, sys.stderr = _routed(stdout), _routed(stderr)
    for handler, stream in handlers:
        handler.setStream(_routed(stream))
    try:
        yield
    finally:
        sys.stdout, sys.stderr = stdout, stderr
        for handler, stream in handlers:
            handler.setStream(stream)


def _routed(target: TextIO) -> TextIO:
    # a duck-typed stand-in rather than an io.TextIOBase subclass, whose finalizer would flush a target closed by then
    return cast("TextIO", _RoutedStream(target))


class _RoutedStream:
    def __init__(self, target: TextIO) -> None:
        self._target: Final[TextIO] = target

    def __getattr__(self, name: str) -> object:
        return getattr(self._target, name)

    def write(self, text: str) -> int:
        if (slot := _SLOT.get()) is None:
            return self._target.write(text)
        with slot.turn:
            if slot.live:
                return self._target.write(text)
            slot.chunks.append((self._target, text))
        return len(text)

    def flush(self) -> None:
        if (slot := _SLOT.get()) is None or slot.live:
            self._target.flush()


__all__ = [
    "fan_out",
    "in_turn",
    "output_is_held",
    "stopped_on_interrupt",
]
