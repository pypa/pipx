#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import os
import sys
import textwrap
from typing import Optional
from pipx.emojies import WINDOWS, stars, hazard


def echo(msg=""):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def ensure_pipx_on_path(bin_dir: Path):
    shell = os.environ.get("SHELL", "")
    config_file: Optional[str]
    if "bash" in shell:
        config_file = "~/.bashrc"
    elif "zsh" in shell:
        config_file = "~/.zshrc"
    elif "fish" in shell:
        config_file = "~/.config/fish/config.fish"
    else:
        config_file = None

    if config_file:
        config_file = os.path.expanduser(config_file)

    if config_file and os.path.exists(config_file):
        with open(config_file, "a") as f:
            f.write("\n# added by pipx (https://github.com/cs01/pipx)\n")
            if "fish" in shell:
                f.write("set -x PATH %s $PATH\n\n" % bin_dir)
            else:
                f.write('export PATH="%s:$PATH"\n' % bin_dir)
        print(f"Added {str(bin_dir)} to the PATH environment variable in {config_file}")
        print("")
        print(f"Open a new terminal to use pipx {stars}")
    else:
        if WINDOWS:
            textwrap.dedent(
                f"""
                Note {hazard}:
                To finish installation, {str(bin_dir)!r} must be added to your PATH
                environment variable.

                To do this, go to settings and type "Environment Variables".
                In the Environment Variables window edit the PATH variable
                by adding the following to the end of the value, then open a new
                terminal.

                    ;{str(bin_dir)}
            """
            )

        else:
            echo(
                textwrap.dedent(
                    f"""
                    Note:
                    To finish installation, {str(bin_dir)!r} must be added to your PATH
                    environemnt variable.

                    To do this, add the following line to your shell
                    config file (such as ~/.bashrc if using bash):

                        export PATH={str(bin_dir)}:$PATH
                """
                )
            )
