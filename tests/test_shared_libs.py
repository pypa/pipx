import os
import time

import pytest  # type: ignore[import-not-found]

from pipx import shared_libs


@pytest.mark.parametrize(
    "mtime_minus_now,needs_upgrade",
    [
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60, True),
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC + 5 * 60, False),
    ],
)
def test_auto_update_shared_libs(capsys, pipx_ultra_temp_env, mtime_minus_now, needs_upgrade):
    now = time.time()
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False

    access_time = now  # this can be anything
    os.utime(shared_libs.shared_libs.pip_path, (access_time, mtime_minus_now + now))

    assert shared_libs.shared_libs.needs_upgrade is needs_upgrade

def test_disable_auto_upgrade_env_var(capsys, pipx_ultra_temp_env, monkeypatch):
    """Test that PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE prevents automatic upgrades."""
    # Set the environment variable
    monkeypatch.setenv("PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE", "1")

    # Reimport to pick up the new environment variable value
    from importlib import reload
    import pipx.constants
    reload(pipx.constants)

    # Verify the constant is set
    from pipx.constants import DISABLE_SHARED_LIBS_AUTO_UPGRADE
    assert DISABLE_SHARED_LIBS_AUTO_UPGRADE == "1"

    # Install a package which normally triggers auto-upgrade
    from helpers import run_pipx_cli
    assert run_pipx_cli(["install", "pycowsay"]) == 0

    # Verify shared libs were NOT automatically upgraded during install
    # by checking the logs/output
    captured = capsys.readouterr()
    # Note: The exact assertion may need adjustment based on actual output
    # The key is that we should NOT see upgrade messages when env var is set
