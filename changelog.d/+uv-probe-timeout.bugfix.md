Probe a `uv` found on `PATH` before using it, and bound every `uv --version` call with a timeout. A broken or hanging
`uv` on `PATH` previously slipped past discovery and stalled the next command; pipx now skips such a binary and reports
a clear error instead of hanging.
