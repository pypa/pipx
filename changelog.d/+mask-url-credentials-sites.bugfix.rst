Mask URL passwords and tokens in the remaining places that printed or logged them as typed: the ``Injecting packages``
log line, the ``--output json`` error fields of ``inject``, ``install`` and ``uninject``, the progress lines of ``pipx
run`` script dependencies and ``--preinstall``, the local source that ``pipx upgrade`` reports, invalid requirement
errors from manifests and inline script metadata, ``--pip-args`` rejected by the uv backend of ``pipx run``, the "looks
like a path" error, and installer output that pipx captures and logs.
