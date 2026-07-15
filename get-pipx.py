#!/usr/bin/env python3
from __future__ import annotations

import sys


def fail(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    sys.exit(1)


def main() -> None:
    fail(
        "This installation method has been obsoleted. "
        "See https://github.com/pypa/pipx for current installation "
        "instructions."
    )


if __name__ == "__main__":
    main()
