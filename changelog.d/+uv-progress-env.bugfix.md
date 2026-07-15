Stop forcing `UV_NO_PROGRESS=1` on every uv call. The override silenced uv's progress bar even when pipx asked to draw
one, and it ignored a `UV_NO_PROGRESS` already set in the environment. pipx now suppresses the bar only in quiet, JSON,
and non-interactive runs, and defers to the caller's `UV_NO_PROGRESS` when it does want progress shown.
