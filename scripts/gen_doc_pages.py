import os
import sys
from pathlib import Path
from subprocess import check_output
from typing import Optional

import mkdocs_gen_files
from jinja2 import Environment, FileSystemLoader


def get_help(cmd: Optional[str]) -> str:
    base = ["pipx"]
    args = base + ([cmd] if cmd else []) + ["--help"]
    env_patch = os.environ.copy()
    env_patch["PATH"] = os.pathsep.join([str(Path(sys.executable).parent)] + env_patch["PATH"].split(os.pathsep))
    content = check_output(args, text=True, env=env_patch)
    content = content.replace(str(Path("~").expanduser()), "~")
    return f"""
```
{content}
```
"""


params = {
    "install": get_help("install"),
    "installall": get_help("install-all"),
    "uninject": get_help("uninject"),
    "inject": get_help("inject"),
    "upgrade": get_help("upgrade"),
    "upgradeall": get_help("upgrade-all"),
    "upgradeshared": get_help("upgrade-shared"),
    "uninstall": get_help("uninstall"),
    "uninstallall": get_help("uninstall-all"),
    "reinstall": get_help("reinstall"),
    "reinstallall": get_help("reinstall-all"),
    "list": get_help("list"),
    "interpreter": get_help("interpreter"),
    "run": get_help("run"),
    "runpip": get_help("runpip"),
    "ensurepath": get_help("ensurepath"),
    "environment": get_help("environment"),
    "completions": get_help("completions"),
    "usage": get_help(None),
}


env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))

with mkdocs_gen_files.open("docs.md", "wt") as file_handler:
    file_handler.write(env.get_template("docs.md").render(**params))
    file_handler.write("\n")
