#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import textwrap

from build_manpages.manpage import Manpage  # type: ignore

from pipx.main import get_command_parser


def main():
    parser = get_command_parser()
    parser.man_short_description = parser.description.splitlines()[1]

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
        .UR https://pypa.github.io/pipx/
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
