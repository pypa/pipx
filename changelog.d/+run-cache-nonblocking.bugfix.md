Make the expired-cache sweep that runs before `pipx run` non-blocking. pipx used to wait for a lock on every other
cached environment, so a concurrent `pipx run` whose install held one of those locks stalled the new run, a stall that
lasted the whole install on Windows. The sweep now skips any environment another run is holding.
