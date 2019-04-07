#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
from typing import Optional
import getpass
from pipx.main import __version__
import os
from jinja2 import Environment, FileSystemLoader


USER = getpass.getuser()
HOME = os.environ.get("HOME", f"/home/{USER}")


def get_help(pipxcmd: Optional[str]) -> str:
    if pipxcmd:
        cmd = ["pipx", pipxcmd, "--help"]
    else:
        cmd = ["pipx", "--help"]

    helptext = (
        subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
        .stdout.decode()
        .replace(HOME, "/home/USER")
    )
    return f"""
```
{" ".join(cmd)}
{helptext}
```
"""


env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("readme.md")

cmd_help = {
    "usage": get_help(None),
    "ensurepath": get_help("ensurepath"),
    "runpip": get_help("runpip"),
    "install": get_help("install"),
    "upgrade": get_help("upgrade"),
    "upgradeall": get_help("upgrade-all"),
    "inject": get_help("inject"),
    "uninstall": get_help("uninstall"),
    "uninstallall": get_help("uninstall-all"),
    "reinstallall": get_help("reinstall-all"),
    "list": get_help("list"),
    "run": get_help("run"),
    "version": __version__,
}

with open("README.md", "wb") as f:
    f.write(template.render(**cmd_help).encode())
