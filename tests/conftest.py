import os
from pathlib import Path

import pytest  # type: ignore

from pipx import constants

# we keep /usr/bin because it enables C-compiling python modules on macOS
PATH_KEEPLIST = ["/usr/bin"]


@pytest.fixture
def pipx_temp_env(tmp_path, monkeypatch):
    """Sets up temporary paths for pipx to install into.

    Also adds environment variables as necessary to make pip installations
    seamless.
    """
    shared_dir = Path(tmp_path) / "shareddir"
    home_dir = Path(tmp_path) / "subdir" / "pipxhome"
    bin_dir = Path(tmp_path) / "otherdir" / "pipxbindir"

    monkeypatch.setattr(constants, "PIPX_SHARED_LIBS", shared_dir)
    monkeypatch.setattr(constants, "PIPX_HOME", home_dir)
    monkeypatch.setattr(constants, "LOCAL_BIN_DIR", bin_dir)
    monkeypatch.setattr(constants, "PIPX_LOCAL_VENVS", home_dir / "venvs")
    monkeypatch.setattr(constants, "PIPX_VENV_CACHEDIR", home_dir / ".cache")

    path_keep = [
        x for x in os.getenv("PATH", "").split(os.pathsep) if x in PATH_KEEPLIST
    ]
    monkeypatch.setenv("PATH", ":".join([str(bin_dir)] + path_keep))
