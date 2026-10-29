Keep the environment when ``pipx install --force`` or ``pipx install-all --force`` cannot move it aside before a
``Requires-Python`` rebuild. On Windows the move fails while any file inside the environment is open, and pipx then
deleted the environment and reported a ``FileNotFoundError`` instead of the real error. pipx now retries the move the
way ``pipx reinstall`` does, and if it still fails it leaves the environment in place and reports the original error.
