import os
import time
import pytest
from pipx import shared_libs


now = time.time()


@pytest.mark.parametrize(
    "mtime,needs_upgrade",
    [
        (now - shared_libs.SHARED_LIBS_MAX_AGE_SEC - 600, True),
        (now - shared_libs.SHARED_LIBS_MAX_AGE_SEC + 600, False),
    ],
)
def test_auto_update_shared_libs(capsys, pipx_temp_env, mtime, needs_upgrade):
    print("now is", now)
    print("mtime is", mtime)
    shared_libs.shared_libs.create([], verbose=True)

    access_time = now  # this can be anything
    os.utime(shared_libs.shared_libs.pip_path, (access_time, mtime))

    assert shared_libs.shared_libs.needs_upgrade is needs_upgrade
