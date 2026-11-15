from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_URL_CREDENTIALS: Final[re.Pattern[str]] = re.compile(r"(?<=://)([^/?#\r\n]*)@")


def redact_command_line(cmd: Sequence[str | Path]) -> str:
    """Redact the credentials in each argument of a command line.

    :param cmd: the command line, as a sequence of arguments.
    :returns: the command line as a single string with the credentials masked.
    """
    return " ".join(redact_url_credentials(str(c)) for c in cmd)


def redact_url_credentials(text: str) -> str:
    """Mask the credentials in the URLs of a text.

    :param text: the text that may hold URLs.
    :returns: the text with the user information of each URL masked.
    """
    # index and package URLs can carry credentials, which must not reach the log file or the verbose output. A bare user
    # such as git@ may be a token, and so may the user before an empty or placeholder password (TOKEN:@), so with a
    # colon both parts are masked.
    #
    # The authority ends at the first /, ? or #, and its userinfo runs to the last @ before that. A password may hold a
    # space, so callers mask each argument before joining a command line; a line break still ends it, as installer
    # output holds a URL per line. Across a space the match can start at a bare token and end at a later word's @, so a
    # user part holding an @ is masked as a bare user.
    return _URL_CREDENTIALS.sub(
        lambda match: "****:****@" if (userinfo := match[1].partition(":"))[1] and "@" not in userinfo[0] else "****@",
        text,
    )


__all__ = [
    "redact_command_line",
    "redact_url_credentials",
]
