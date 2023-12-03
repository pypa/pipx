import sys
from pathlib import Path
from subprocess import check_output
from typing import Optional

import mkdocs_gen_files
from jinja2 import Environment, FileSystemLoader

from pipx.main import __version__


def get_help(cmd: Optional[str]) -> str:
    base = [sys.executable, "-m", "pipx"]
    args = base + ([cmd] if cmd else []) + ["--help"]
    content = check_output(args, text=True)
    content = content.replace(str(Path("~").expanduser()), "~")
    return f"""
```
{" ".join(args[2:])}
{content}
```
"""


params = {
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
    "usage": get_help(None),
}


env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))

with mkdocs_gen_files.open("docs.md", "wt") as file_handler:
    file_handler.write(env.get_template("docs.md").render(**params))
    file_handler.write("\n")

with mkdocs_gen_files.open("changelog.md", "rt") as file_handler:
    text = file_handler.read()
with mkdocs_gen_files.open("changelog.md", "wt") as file_handler:
    file_handler.write(f"## {__version__}" + text[len("## dev") :])
