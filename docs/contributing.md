pipx uses [tox](https://pypi.org/project/tox/) for development, continuous integration testing, and automation.

## Developing pipx

To develop `pipx`, first clone the repository, have `tox` installed somewhere on your system, then run:
```
tox --notest
```

This will perform an editable install of `pipx` for each environment listed in `envlist` in the `tox.ini`. Currently, this is only `py36`. Enter the virtualenv with `source .tox/py36/bin/activate`. Any changes you make to pipx source code will be reflected immediately in the virtualenv's `pipx` executable.

Make sure your changes pass tests by first exiting the virtual environment, then running `tox`.


## Documentation

Documentation is generated with `mkdocs` which generates documentation from several `.md` files in `docs`. Some of those `.md` files, as well as the main `README.md` file are generated from a `templates` directory.

First, build the documentation virtualenv with `tox -e docs`. This will also build the documentation.

If you make changes to any template files, enter the virtualenv: `source .tox/docs/bin/activate`. Rebuild the documentation with `mkdocs build`. To serve documentation, `mkdocs serve`. To publish documentation to GitHub pages, `mkdocs gh-deploy`.
