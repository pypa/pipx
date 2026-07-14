## Shell Completion

You can easily get your shell's tab completions working by following instructions printed with this command:

```
pipx completions
```

## Completions for the packages you install

A package can ship the completion script for its own command, the way it ships a man page. pipx links that script out of
the environment it installed it into, so the completions arrive with the package and leave with it.

pipx picks up the three directories a wheel installs completion scripts into and links each one under
`PIPX_COMPLETION_DIR`, which defaults to `~/.local/share`:

| Shipped by the package               | Linked to                                     | Loaded by            |
| ------------------------------------ | --------------------------------------------- | -------------------- |
| `share/bash-completion/completions/` | `~/.local/share/bash-completion/completions/` | bash, on its own     |
| `share/fish/vendor_completions.d/`   | `~/.local/share/fish/vendor_completions.d/`   | fish, on its own     |
| `share/zsh/site-functions/`          | `~/.local/share/zsh/site-functions/`          | zsh, once you say so |

bash and fish read their directories without further help. zsh needs the directory on its `fpath`, so add this to your
`~/.zshrc` ahead of the call to `compinit`:

```
fpath+=("$(pipx environment --value PIPX_COMPLETION_DIR)/zsh/site-functions")
```

`pipx uninstall` takes the links away, and `pipx unexpose` removes them while leaving the package in place.

To ship completions from your own package, install them through the data files of your build backend. With setuptools:

```python
setup(
    name="your-tool",
    data_files=[
        ("share/bash-completion/completions", ["completions/your-tool"]),
        ("share/zsh/site-functions", ["completions/_your-tool"]),
        ("share/fish/vendor_completions.d", ["completions/your-tool.fish"]),
    ],
)
```
