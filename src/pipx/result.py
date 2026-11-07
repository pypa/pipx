from __future__ import annotations

__lazy_modules__ = ["json"]

import enum
import json
import logging
import sys
from dataclasses import asdict, dataclass
from typing import Any, Final, Generic, TypeVar

from pipx.constants import EXIT_CODE_OK, ExitCode

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class OutputLevel(enum.IntEnum):
    """Severity of an output message."""

    NORMAL = 0
    ERROR = 1
    CRITICAL = 2


class OutputStream(enum.StrEnum):
    """Stream that an output message is written to."""

    LOG = "log"
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True, slots=True, kw_only=True)
class OutputMessage:
    """A line of output with its stream and severity.

    :param text: the line of output.
    :param stream: the stream the line is written to.
    :param level: the severity of the line.
    :param notice: whether the line reports a choice pipx made on the user's behalf.
    """

    text: str
    stream: OutputStream = OutputStream.STDOUT
    level: OutputLevel = OutputLevel.NORMAL
    # a choice pipx made on the user's behalf, which JSON output still reports on stderr beside the envelope
    notice: bool = False


# scripts key on the code and the identity fields, so they stay stable across releases
@dataclass(frozen=True, slots=True, kw_only=True)
class OperationError:
    """An error that a command reports in its result.

    :param code: the code that scripts key on.
    :param message: the description of the error for people.
    :param environment: the environment the error relates to, or None.
    :param package: the package the error relates to, or None.
    """

    code: str
    message: str
    environment: str | None = None
    package: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationData:
    """Base class of the data that a command returns."""

    def to_dict(self) -> dict[str, Any]:
        """Return the data as a dictionary.

        :returns: the fields of the data.
        """
        return asdict(self)


_PayloadT = TypeVar("_PayloadT", bound=OperationData)


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationResult(Generic[_PayloadT]):
    """The outcome of a command: its messages, its exit code and its data.

    :param command: the command that produced the result.
    :param data: the data the command returned.
    :param messages: the output messages the command produced.
    :param exit_code: the exit code of the command.
    :param errors: the errors the command reported.
    :param succeeded: whether at least one operation produced a successful outcome.
    """

    command: tuple[str, ...]
    data: _PayloadT
    messages: tuple[OutputMessage, ...] = ()
    exit_code: ExitCode = EXIT_CODE_OK
    errors: tuple[OperationError, ...] = ()
    # whether the operation produced at least one successful outcome; distinguishes a partial run from a total failure
    succeeded: bool = False

    @property
    def status(self) -> str:
        """Return ``success``, ``partial`` or ``error``, from whether any error was reported and the command succeeded.

        :returns: the status of the command.
        """
        if not self.errors:
            return "success"
        return "partial" if self.succeeded else "error"


def render_result(result: OperationResult[_PayloadT], *, output: OutputFormat, quiet: int) -> ExitCode:
    """Print a result in the requested format and return its exit code.

    :param result: the result of the command.
    :param output: the format to print the result in.
    :param quiet: the level below which messages are not printed.
    :returns: the exit code of the command.
    """
    if output is OutputFormat.JSON:
        envelope: Final[str] = _render_envelope(
            result.command, result.status, result.exit_code, result.data.to_dict(), result.errors
        )
        print(envelope)  # ruff:ignore[print]  # the JSON envelope is the command's machine-readable stdout payload
        for message in result.messages:
            if message.notice:
                print(message.text, file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        return result.exit_code

    render_messages(result.messages, quiet=quiet)
    return result.exit_code


class OutputFormat(enum.StrEnum):
    """Format of the command output."""

    HUMAN = "human"
    JSON = "json"


def _render_envelope(
    command: tuple[str, ...],
    status: str,
    exit_code: ExitCode,
    data: dict[str, Any],
    errors: tuple[OperationError, ...],
) -> str:
    return json.dumps(
        {
            "pipx_result_version": "1",
            "command": list(command),
            "status": status,
            "exit_code": int(exit_code),
            "data": data,
            "errors": [asdict(error) for error in errors],
        },
        indent=2,
        sort_keys=True,
    )


def render_messages(messages: tuple[OutputMessage, ...], *, quiet: int) -> None:
    """Print messages to their streams, skipping those below the quiet level.

    :param messages: the messages to print.
    :param quiet: the level below which messages are not printed.
    """
    for message in messages:
        if quiet <= message.level:
            if message.stream is OutputStream.LOG:
                _LOGGER.warning(message.text)
            else:
                print(message.text, file=sys.stderr if message.stream is OutputStream.STDERR else sys.stdout)


def error_envelope(command: tuple[str, ...], error: OperationError, exit_code: ExitCode) -> str:
    """Render an error as the JSON envelope that a command prints.

    :param command: the command that failed.
    :param error: the error to render.
    :param exit_code: the exit code of the command.
    :returns: the JSON text.
    """
    return _render_envelope(command, "error", exit_code, {}, (error,))


__all__ = [
    "OperationData",
    "OperationError",
    "OperationResult",
    "OutputFormat",
    "OutputLevel",
    "OutputMessage",
    "OutputStream",
    "error_envelope",
    "render_messages",
    "render_result",
]
