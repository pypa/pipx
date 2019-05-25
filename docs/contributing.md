pipx uses [tox](https://pypi.org/project/tox/) for development, continuous integration testing, and automation.

## Developing pipx
To develop `pipx`, first clone the repository, have `tox` installed somewhere on your system, then run:
```
tox --notest
```

This will perform an editable install of `pipx` for each environment listed in `envlist` in the `tox.ini`. Any changes you make to pipx source code will be reflected immediately, if you invoke `pipx` in the virtual environment like so:
```
.tox/py36/bin/pipx
```

Make sure your changes pass tests:
```
tox
```

## Documentation
Documentation is generated with `mkdocs` which generates documentation from several `.md` files in `docs`. Some of those `.md` files, as well as the main `README.md` file are generated from a `templates` directory.

First, build the documentation virtualenv with `tox -e docs`. This will also build the documentation.

If you make changes to any template files, rebuild the documentation with `.tox/docs/bin/mkdocs build`. To serve documentation, `.tox/docs/bin/mkdocs serve`.


### Publishing
To publish documentation to GitHub pages:
```
.tox/docs/bin/mkdocs gh-pages
```

When finished, you may remove the virtual environment with `rm -r .tox`.

