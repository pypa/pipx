from pathlib import Path

import pytest  # type: ignore

from pipx import constants, shared_libs


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
    shared_libs.PIPX_SHARED_LIBS = shared_dir
    shared_libs.shared_libs.__init__()
    monkeypatch.setattr(constants, "PIPX_HOME", home_dir)
    monkeypatch.setattr(constants, "LOCAL_BIN_DIR", bin_dir)
    monkeypatch.setattr(constants, "PIPX_LOCAL_VENVS", home_dir / "venvs")
    monkeypatch.setattr(constants, "PIPX_VENV_CACHEDIR", home_dir / ".cache")

    monkeypatch.setenv("PATH", str(bin_dir))
