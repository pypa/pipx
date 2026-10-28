The uv backend no longer applies a ``uv.toml`` or ``pyproject.toml`` found in the directory uv runs in or any parent,
such as one another local account wrote to a shared ``/tmp``. pipx now sets ``UV_NO_CONFIG=1`` for its ``uv venv`` and
``uv pip`` calls and passes ``--no-config`` to ``uv run --script``. This also stops those calls from reading your user
and system ``uv.toml``; set ``UV_CONFIG_FILE`` to apply one.
