Include `pipx run --with` packages in the run-cache key. Because they were absent, `pipx run TOOL` and
`pipx run --with EXTRA TOOL` shared one cached environment, so extras injected by one invocation leaked into later runs
that asked for none. Each distinct set of extras now gets its own environment, and the extras are injected only when
that environment is first built.
