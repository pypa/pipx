## Using pipx with pre-commit

pipx has [pre-commit](https://pre-commit.com/) support. This lets you run applications:

- that can be run using `pipx run` but don't have native pre-commit support;
- using its prebuilt wheel from pypi.org instead of building it from source; and
- using pipx's `--spec` and `--index-url` flags.

Example configuration for use of the code linter [yapf](https://github.com/google/yapf/). This is to be added to your
`.pre-commit-config.yaml`.

```yaml
  - repo: https://github.com/pypa/pipx
    rev: 1.5.0
    hooks:
      - id: pipx
        alias: yapf
        name: yapf
        args: [yapf, -i]
        types: [python]
```
