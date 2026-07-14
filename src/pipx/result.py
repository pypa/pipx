import enum
import json
import logging
import sys
from dataclasses import asdict, dataclass
from typing import Any, Final, Generic, TypeVar

from pipx.constants import EXIT_CODE_OK, ExitCode

PIPX_RESULT_VERSION: Final[str] = "0.1"

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
class OperationData:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PayloadT = TypeVar("_PayloadT", bound=OperationData)


@dataclass(frozen=True)
class OperationResult(Generic[_PayloadT]):
    command: str
    data: _PayloadT
    messages: tuple[OutputMessage, ...] = ()
    exit_code: ExitCode = EXIT_CODE_OK


def render_messages(messages: tuple[OutputMessage, ...], *, quiet: int) -> None:
    for message in messages:
        if quiet <= message.level:
            if message.stream is OutputStream.LOG:
                _LOGGER.warning(message.text)
            else:
                print(message.text, file=sys.stderr if message.stream is OutputStream.STDERR else sys.stdout)


def render_result(result: OperationResult[_PayloadT], *, output: OutputFormat, quiet: int) -> ExitCode:
    if output is OutputFormat.JSON:
        print(
            json.dumps(
                {
                    "pipx_result_version": PIPX_RESULT_VERSION,
                    "command": result.command,
                    "status": "success" if result.exit_code == EXIT_CODE_OK else "error",
                    "data": result.data.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return result.exit_code

    render_messages(result.messages, quiet=quiet)
    return result.exit_code


__all__ = [
    "OperationData",
    "OperationResult",
    "OutputFormat",
    "OutputLevel",
    "OutputMessage",
    "OutputStream",
    "render_messages",
    "render_result",
]
