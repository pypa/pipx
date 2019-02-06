#!/usr/bin/env python3
import sys


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    sys.exit(1)


def main():
    fail(
        "This installation method has been deprecated. "
        "See https://github.com/pipxproject/pipx for current installation "
        "instructions."
    )


if __name__ == "__main__":
    main()
