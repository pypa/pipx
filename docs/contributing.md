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
Documentation is generated with `mkdocs` which generates documentation from several `.md` files in `docs`. Some of those `.md` files, as well as the main `README.md` file are generated from a `templates` directory.


### Serving
To serve documenation with mkdocs that reflect the content of the `docs` folder as you make changes:
```
tox -e watchdocs
```

As you serve the docs, if you make changes to any template files, you generate the .md files by running:
```
tox -e docs
```


### Publishing
To publish documentation to GitHub pages:
```
mkdocs gh-pages
```

When finished, you may remove the virtual environment with `rm -r .tox`.

