Honour a script's PEP 723 `requires-python` on the pip-backed `pipx run`. Without an explicit `--python`, pipx now picks
an interpreter that satisfies the constraint, matching what the uv backend already does; with an explicit `--python`
that fails the constraint it reports a clear error instead of running on an unsupported interpreter. A malformed inline
metadata block now produces a readable message rather than a traceback.
