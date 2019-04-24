pipx uses [tox](https://pypi.org/project/tox/) for development and continuous integration testing and automation.

## Developing pipx
To develop `pipx` first clone the repository, have `tox` installed somewhere on your system, then run `tox`.
```
tox --notest
```

Tox creates virtual environments in `.tox/` (`.tox/python` is the default). Make any changes and then invoke `pipx` like this:
```
.tox/python/bin/pipx ...
```
Any changes you make to pipx source code will be reflected immediately.

Make sure your changes pass tests by running tox
```
tox
```

## Documentation
Documentation is made with `mkdocs` which generates documentation from several `.md` files in `docs`.

To serve documenation with mkdocs that reflect the content of the `docs` folder as you make changes:
```
tox -e watchdocs
```

To build the documentation:
```
tox -e docs
```

Note that some of the documentation is generated. This occurs during the build command.

When finished, you may remove the virtual environment with `rm -r .tox`.
