#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import textwrap
from argparse import (
    SUPPRESS,
    Action,
    ArgumentParser,
    _SubParsersAction,  # ruff:ignore[import-private-name]  # argparse exposes no public subparser type
)
from pathlib import Path


def main() -> None:
    documented_python = os.environ.get("PIPX__DOC_DEFAULT_PYTHON")
    os.environ["PIPX__DOC_DEFAULT_PYTHON"] = "python3"
    original_program = sys.argv[0]
    sys.argv[0] = "pipx"
    try:
        from pipx.main import (
            get_command_parser,  # pipx reads the documentation environment on import.
        )

        parser, _ = get_command_parser()
    finally:
        sys.argv[0] = original_program
        if documented_python is None:
            os.environ.pop("PIPX__DOC_DEFAULT_PYTHON")
        else:
            os.environ["PIPX__DOC_DEFAULT_PYTHON"] = documented_python

    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/man/pipx.1.rst")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_generate_manpage_rst(parser), encoding="utf-8")


def _generate_manpage_rst(parser: ArgumentParser) -> str:
    commands = _get_subcommands(parser)
    synopsis_commands = " | ".join(f"**{name}**" for name, _ in commands)
    lines = [
        ":orphan:",
        "",
        "====",
        "pipx",
        "====",
        "",
        "-" * 60,
        "install and run Python applications in isolated environments",
        "-" * 60,
        "",
        ":Manual section: 1",
        ":Manual group: User Commands",
        "",
        "SYNOPSIS",
        "--------",
        "",
        *textwrap.wrap(f"**pipx** [*global-options*] [{synopsis_commands}] [*command-options*]", width=120),
        "",
        "DESCRIPTION",
        "-----------",
        "",
        "pipx installs and runs Python applications in isolated environments while exposing their commands on your",
        "``PATH``.",
        "",
    ]
    lines.extend(_commands_section(commands))
    lines.extend(_global_options_section(parser))
    lines.extend(_static_sections())
    return "\n".join(lines) + "\n"


def _get_subcommands(parser: ArgumentParser) -> list[tuple[str, str]]:
    if parser._subparsers is None:  # ruff:ignore[private-member-access]  # argparse exposes no public subparser API
        return []
    for action in parser._subparsers._actions:  # ruff:ignore[private-member-access]  # argparse exposes no public subparser API
        if isinstance(action, _SubParsersAction):
            return [(choice.dest, choice.help or "") for choice in action._choices_actions]  # ruff:ignore[private-member-access]  # argparse exposes no public subparser API
    return []


def _commands_section(commands: list[tuple[str, str]]) -> list[str]:
    lines = ["COMMANDS", "--------", ""]
    for name, help_text in commands:
        lines.append(f"**{name}**")
        lines.extend(f"    {line}" for line in textwrap.wrap(help_text.replace("`", "``"), width=116))
        lines.append("")
    lines.extend(["Run **pipx** *command* **--help** for command-specific options.", ""])
    return lines


def _global_options_section(parser: ArgumentParser) -> list[str]:
    lines = ["GLOBAL OPTIONS", "--------------", ""]
    seen: set[int] = set()
    for action in parser._actions:  # ruff:ignore[private-member-access]  # argparse exposes no public action list API
        if id(action) in seen or action.help == SUPPRESS or isinstance(action, _SubParsersAction):
            continue
        seen.add(id(action))
        if option := _format_option(action):
            lines.extend([option, f"    {action.help}", ""])
    return lines


def _format_option(action: Action) -> str:
    if not action.option_strings or not action.help:
        return ""
    option = ", ".join(f"**{value}**" for value in action.option_strings)
    if action.metavar:
        metavar = action.metavar if isinstance(action.metavar, str) else action.metavar[0]
        option += f" *{metavar}*"
    return option


def _static_sections() -> list[str]:
    return [
        "ENVIRONMENT VARIABLES",
        "---------------------",
        "",
        "**PIPX_HOME**",
        "    Directory for pipx-managed environments and state.",
        "",
        "**PIPX_BIN_DIR**",
        "    Directory where pipx exposes application commands.",
        "",
        "**PIPX_DEFAULT_PYTHON**",
        "    Default interpreter used to create environments.",
        "",
        "**PIPX_USE_EMOJI**",
        "    Set to ``0`` to disable emoji output.",
        "",
        "SEE ALSO",
        "--------",
        "",
        "Full documentation: https://pipx.pypa.io/",
        "",
        r"**pip**\(1), **virtualenv**\(1)",
        "",
        "AUTHORS",
        "-------",
        "",
        "Chad Smith and contributors",
        "",
        "https://github.com/pypa/pipx",
    ]


if __name__ == "__main__":
    main()
