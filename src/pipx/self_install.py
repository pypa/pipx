from __future__ import annotations

__lazy_modules__ = ["json", "shutil", "typing"]

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Final, TypeAlias

_JsonValue: TypeAlias = bool | int | float | str | list["_JsonValue"] | dict[str, "_JsonValue"] | None
_PIPX_METADATA_FILENAME: Final[str] = "pipx_metadata.json"
DEFAULT_PIPX_GLOBAL_HOME: Final[Path] = Path("/opt/pipx")


def discover_self_managed_environment() -> dict[str, str]:
    if os.name == "nt":
        return {}

    venv: Final[Path] = Path(sys.prefix)
    if venv.parent.name != "venvs":
        return {}

    try:
        metadata: Final[_JsonValue] = json.loads((venv / _PIPX_METADATA_FILENAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(metadata, dict):
        return {}
    main_package: Final[_JsonValue] = metadata.get("main_package")
    if not isinstance(main_package, dict) or main_package.get("package") != "pipx":
        return {}

    environment: Final[dict[str, str]] = {}
    global_home: Final[Path] = Path(os.environ.get("PIPX_GLOBAL_HOME") or DEFAULT_PIPX_GLOBAL_HOME).expanduser()
    # a pipx installed with --global serves every user, so only --global may select the global paths
    if (home := venv.parent.parent).resolve() != global_home.resolve():
        environment["PIPX_HOME"] = str(home)
        invoked_executable: Final[Path | None] = _invoked_executable(sys.argv[0])
        # only the exposed link, a link outside the venv that leads into it, names the bin directory; compare real
        # locations, as ".." or a symlinked directory spell the venv's own script as a path outside the venv
        real_venv: Final[Path] = venv.resolve()
        if (
            invoked_executable is not None
            and not invoked_executable.parent.resolve().is_relative_to(real_venv)
            and invoked_executable.resolve().is_relative_to(real_venv)
        ):
            environment["PIPX_BIN_DIR"] = str(invoked_executable.parent)

    source_interpreter: Final[_JsonValue] = metadata.get("source_interpreter")
    if (
        isinstance(source_interpreter, dict)
        and source_interpreter.get("__type__") == "Path"
        and isinstance(source_path := source_interpreter.get("__Path__"), str)
        and backs_self_managed_venv(Path(source_path), venv)
    ):
        environment["PIPX_DEFAULT_PYTHON"] = source_path
    return environment


def backs_self_managed_venv(source_interpreter: Path, venv: Path) -> bool:
    # a record pointing at a since-removed bootstrap venv must not outlive it or adopt whatever appears there later
    return source_interpreter.resolve() == (venv / "bin" / "python").resolve()


def _invoked_executable(executable: str) -> Path | None:
    if os.sep in executable or (os.altsep is not None and os.altsep in executable):
        return Path(executable).absolute()
    if found := shutil.which(executable):
        return Path(found)
    return None


_SELF_MANAGED_ENVIRONMENT: Final[dict[str, str]] = discover_self_managed_environment()


def get_environment_value(name: str) -> str | None:
    return os.environ.get(name, _SELF_MANAGED_ENVIRONMENT.get(name))


__all__ = [
    "DEFAULT_PIPX_GLOBAL_HOME",
    "backs_self_managed_venv",
    "discover_self_managed_environment",
    "get_environment_value",
]
