pipx uses [nox](https://pypi.org/project/nox/) for development, continuous integration testing, and automation.

## Developing pipx
pipx uses pipx to develop -- it's recursive! But don't worry, it's not that scary. You'll be up in running in no time. You'll also need `make` installed. If you don't have `make`, you can look at pipx's `makefile` to see the what the make targets correspond to).

To develop `pipx`, first clone the repository.

Next, run this command which will use the amazing [nox](https://github.com/theacodes/nox) automation framework to set up a virtual environment for each Python version pipx tests against.
```
make develop
```

A virtual environment with required dependencies is now sandboxed and ready to go in `.nox/develop-3.6` for Python 3.6. Any changes you make to pipx source code will be reflected immediately in the virtual environment inside `.nox/develop-3.6`.

So how do you run with that environment?

You can  either enter the virtual environment with `source .nox/develop-3.6/bin/activate` and run `pipx`, or you can run the development `pipx` directly with `.nox/develop-3.6/bin/pipx`. Either way, it's running directly from the source code you just cloned and will reflect any changes you make. In one case the command is a bit longer but your environment isn't modified. In the other, you can type `pipx` but you have to enter the virtual environment. Whichever you prefer will work fine. Go ahead and make your changes now.

## Testing pipx locally
pipx uses the test automation framework [nox](https://github.com/theacodes/nox). Test definitions live in `noxfile.py`.

Run tests by exiting any virtual environment, then running
```
make test
```

## Testing pipx on Continuous Intergration builds
When you push a new git branch, tests will automatically be run against your code as defined in `.travis`.

## Documentation

Documentation has a couple steps to it, both of which are automated. The first step is to generate markdown files from templates. See the `templates` directory. The generated files will have a header at the top indicating they were generated and shouldn't be manually modified. Modify the templates, not the generated markdown files.

The second is to compile the markdown files in `docs` with `mkdocs`.

Both of these steps are done in a single build command:
```
make docs
```

To preview changes, including live reloading, open another terminal and run
```
make watch_docs
```

If you make changes to the pipx cli api or any template, regenerate the `.md` files in the `docs` folder:
```
make docs
```

### Publishing Doc Changes to GitHub pages
```
make publish_docs
```

## Release New `pipx` Version
To create a new release
* make sure the changelog is updated
* update the version of pipx defined in `setup.py`

Finally, run
```
make publish
```
and don't forget to publish updated documenation.
