from pipx.constants import (
    EXIT_CODE_OK,
    LOCAL_BIN_DIR,
    PIPX_HOME,
    PIPX_LOCAL_VENVS,
    PIPX_LOG_DIR,
    PIPX_SHARED_LIBS,
    PIPX_TRASH_DIR,
    PIPX_VENV_CACHEDIR,
    ExitCode,
)


def environment(value: str) -> ExitCode:
    """Print a list of variables used in `pipx.constants`"""
    if value is None:
        print(f"PIPX_HOME={PIPX_HOME}")
        print(f"PIPX_BIN_DIR={LOCAL_BIN_DIR}")
        print(f"PIPX_SHARED_LIBS={PIPX_SHARED_LIBS}")
        print(f"PIPX_LOCAL_VENVS={PIPX_LOCAL_VENVS}")
        print(f"PIPX_LOG_DIR={PIPX_LOG_DIR}")
        print(f"PIPX_TRASH_DIR={PIPX_TRASH_DIR}")
        print(f"PIPX_VENV_CACHEDIR={PIPX_VENV_CACHEDIR}")
    elif "PIPX_HOME" in value:
        print(PIPX_HOME)
    elif "PIPX_BIN_DIR" in value:
        print(LOCAL_BIN_DIR)
    elif "PIPX_SHARED_LIBS" in value:
        print(PIPX_SHARED_LIBS)
    elif "PIPX_LOCAL_VENVS" in value:
        print(PIPX_LOCAL_VENVS)
    elif "PIPX_LOG_DIR" in value:
        print(PIPX_LOG_DIR)
    elif "PIPX_TRASH_DIR" in value:
        print(PIPX_TRASH_DIR)
    elif "PIPX_VENV_CACHEDIR" in value:
        print(PIPX_VENV_CACHEDIR)
    else:
        print("Variable not found.")

    return EXIT_CODE_OK
