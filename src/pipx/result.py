from __future__ import annotations

import enum
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Final, Generic, TypeVar

from pipx.constants import EXIT_CODE_OK, ExitCode

PIPX_RESULT_VERSION: Final[str] = "1"

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class OutputLevel(enum.IntEnum):
    NORMAL = 0
    ERROR = 1
    CRITICAL = 2


class OutputFormat(str, enum.Enum):
    HUMAN = "human"
    JSON = "json"


class OutputStream(str, enum.Enum):
    LOG = "log"
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True)
class OutputMessage:
    text: str
    stream: OutputStream = OutputStream.STDOUT
    level: OutputLevel = OutputLevel.NORMAL


@dataclass(frozen=True)
class OperationError:
    """A single failure inside a structured result, with a stable code and the identity fields scripts key on."""

    code: str
    message: str
    environment: str | None = None
    package: str | None = None


@dataclass(frozen=True)
class OperationData:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PayloadT = TypeVar("_PayloadT", bound=OperationData)


@dataclass(frozen=True)
class OperationResult(Generic[_PayloadT]):
    command: tuple[str, ...]
    data: _PayloadT
    messages: tuple[OutputMessage, ...] = ()
    exit_code: ExitCode = EXIT_CODE_OK
    errors: tuple[OperationError, ...] = ()
    # whether the operation produced at least one successful outcome; distinguishes a partial run from a total failure
    succeeded: bool = field(default=False)

    @property
    def status(self) -> str:
        if not self.errors:
            return "success"
        return "partial" if self.succeeded else "error"


def render_messages(messages: tuple[OutputMessage, ...], *, quiet: int) -> None:
    for message in messages:
        if quiet <= message.level:
            if message.stream is OutputStream.LOG:
                _LOGGER.warning(message.text)
            else:
                print(message.text, file=sys.stderr if message.stream is OutputStream.STDERR else sys.stdout)


def error_envelope(command: tuple[str, ...], error: OperationError, exit_code: ExitCode) -> str:
    return _render_envelope(command, "error", exit_code, {}, (error,))


def render_result(result: OperationResult[_PayloadT], *, output: OutputFormat, quiet: int) -> ExitCode:
    if output is OutputFormat.JSON:
        envelope = _render_envelope(
            result.command, result.status, result.exit_code, result.data.to_dict(), result.errors
        )
        print(envelope)  # noqa: T201  # the JSON envelope is the command's machine-readable stdout payload
        return result.exit_code

    render_messages(result.messages, quiet=quiet)
    return result.exit_code


def _render_envelope(
    command: tuple[str, ...],
    status: str,
    exit_code: ExitCode,
    data: dict[str, Any],
    errors: tuple[OperationError, ...],
) -> str:
    return json.dumps(
        {
            "pipx_result_version": PIPX_RESULT_VERSION,
            "command": list(command),
            "status": status,
            "exit_code": int(exit_code),
            "data": data,
            "errors": [asdict(error) for error in errors],
        },
        indent=2,
        sort_keys=True,
    )


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
