Group the manifest commands under `pipx manifest`: use `pipx manifest lock` and `pipx manifest sync` in place of the
top-level `pipx lock` and `pipx sync`. Keeping both verbs under one noun matches `pipx cache` and `pipx interpreter` and
leaves the top-level command list about the manifest rather than two loose verbs.
