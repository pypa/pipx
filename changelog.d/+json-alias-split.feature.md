Keep `--json` only on `pipx list`, where it prints the versioned package snapshot that `install-all` reads back. Every
other command dropped the `--json` alias in favour of `--output json`, so the snapshot format and the result envelope no
longer share a flag.
