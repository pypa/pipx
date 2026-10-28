``pipx uninject`` no longer removes apps, man pages and completions that the main package or another injected package of
the environment still exposes, such as a command of a dependency both packages share under ``--include-deps``.
