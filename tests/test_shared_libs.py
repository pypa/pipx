import os
import time

import pytest  # type: ignore

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
