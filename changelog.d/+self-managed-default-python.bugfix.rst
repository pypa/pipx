A self-managed pipx no longer adopts a recorded default interpreter that no longer backs its own environment, such as
the ``python3`` of a bootstrap environment removed after ``pipx install pipx --python python3``. pipx failed every
command with a ``PIPX_DEFAULT_PYTHON`` error, or built new environments on whatever appeared at that path later.
