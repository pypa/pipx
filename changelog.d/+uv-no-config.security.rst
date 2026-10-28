The uv backend no longer applies a ``uv.toml`` or ``pyproject.toml`` found in the directory uv runs in, the script's
directory, or their parents, such as one another local account wrote to a shared ``/tmp``. pipx now points uv's
project-config search at ``PIPX_HOME`` through ``UV_PROJECT``, and through ``--project`` for ``uv run --script``. Your
user and system ``uv.toml`` and ``UV_CONFIG_FILE`` still apply. Keep ``PIPX_HOME`` out of directories other accounts
can write.
