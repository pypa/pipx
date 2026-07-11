import json
import os
import shutil
import sys
from pathlib import Path
from typing import Final

__all__ = ["SELF_MANAGED_ENVIRONMENT", "discover_self_managed_environment", "get_environment_value"]


def _invoked_executable(executable: str) -> Path | None:
    if os.sep in executable or (os.altsep is not None and os.altsep in executable):
        return Path(executable).absolute()
    if found := shutil.which(executable):
        return Path(found)
    return None


def discover_self_managed_environment(
    prefix: Path | None = None,
    executable: str | None = None,
) -> dict[str, str]:
    if os.name == "nt":
        return {}

    prefix = Path(sys.prefix) if prefix is None else prefix
    if prefix.parent.name != "venvs":
        return {}

    try:
        metadata: object = json.loads((prefix / "pipx_metadata.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(metadata, dict):
        return {}
    main_package = metadata.get("main_package")
    if not isinstance(main_package, dict) or main_package.get("package") != "pipx":
        return {}

    environment: dict[str, str] = {"PIPX_HOME": str(prefix.parent.parent)}
    invoked_executable = _invoked_executable(sys.argv[0] if executable is None else executable)
    if (
        invoked_executable is not None
        and not invoked_executable.is_relative_to(prefix)
        and invoked_executable.resolve().is_relative_to(prefix)
    ):
        environment["PIPX_BIN_DIR"] = str(invoked_executable.parent)

    source_interpreter = metadata.get("source_interpreter")
    if isinstance(source_interpreter, dict) and source_interpreter.get("__type__") == "Path":
        if isinstance(source_path := source_interpreter.get("__Path__"), str):
            environment["PIPX_DEFAULT_PYTHON"] = source_path
    return environment


SELF_MANAGED_ENVIRONMENT: Final[dict[str, str]] = discover_self_managed_environment()


def get_environment_value(name: str) -> str | None:
    return os.environ.get(name, SELF_MANAGED_ENVIRONMENT.get(name))
