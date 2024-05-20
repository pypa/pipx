#!/usr/bin/env python3

import os.path
import sys
import textwrap
from typing import cast

from build_manpages.manpage import Manpage  # type: ignore

from pipx.main import get_command_parser


def main():
    sys.argv[0] = "pipx"
    parser, _ = get_command_parser()
    parser.man_short_description = cast(str, parser.description).splitlines()[1]  # type: ignore[attr-defined]

    manpage = Manpage(parser)
    body = str(manpage)

    # Avoid hardcoding build paths in manpages (and improve readability)
    body = body.replace(os.path.expanduser("~").replace("-", "\\-"), "~")

    # Add a credit section
    body += textwrap.dedent(
        """
        .SH AUTHORS
        .IR pipx (1)
        was written by Chad Smith and contributors.
        The project can be found online at
        .UR https://pipx.pypa.io
        .UE
        .SH SEE ALSO
        .IR pip (1),
        .IR virtualenv (1)
        """
    )

    with open("pipx.1", "w") as f:
        f.write(body)


if __name__ == "__main__":
    main()
