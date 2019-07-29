pipx uses [nox](https://pypi.org/project/nox/) for development, continuous integration testing, and automation.

## Developing pipx

pipx uses pipx to develop -- it's recursive! But don't worry, it's not that scary. You'll be up in running in no time.

To develop `pipx`, first clone the repository, and have a stable version of `pipx` installed.

Next, run this command which will set up a virtual environment for each Python version pipx tests against.
```
pipx run --spec=git+https://github.com/cs01/nox.git@7f65d2abc nox --session develop
```

Alternatively, you can install this version of nox on your system:
```
pip install git+https://github.com/cs01/nox.git@7f65d2abc#egg=nox
```

<details markdown="1">
<summary>pipx requires a branch of <code>nox</code> to run tests at the moment</summary>
For tests to work, pipx requires nox to create virtual environments with venv. nox currently uses virtualenv. pipx uses a fork of nox at https://github.com/cs01/nox on the branch cs01/use-venv until this is fixed in nox. See https://github.com/theacodes/nox/issues/199

</details>

A virtual environment with required dependencies is now sandboxed and ready to go in `.nox/develop-3.6`. Any changes you make to pipx source code will be reflected immediately in the virtual environment inside `.nox/develop-3.6`.

So how do you run with that environment? You can  either enter the virtual environment with `source .nox/develop-3.6/bin/activate` and run `pipx`, or you can run the development `pipx` directly with `.nox/develop-3.6/bin/pipx`. Either way, it's running directly from the source code you just cloned and will reflect any changes you make. In one case the command is a bit longer but your environment isn't modified. In the other, you can type `pipx` but you have to enter the virtual environment. Whichever you prefer will work fine.

## Testing pipx locally
pipx uses the test automation framework [nox](https://github.com/theacodes/nox). Test definitions live in `noxfile.py`.

Run tests by exiting any virtual environment, then running
```
pipx run --spec=git+https://github.com/cs01/nox.git@7f65d2abc nox
```

<details markdown="1">
<summary>pipx requires a branch of <code>nox</code> to run tests at the moment</summary>
For tests to work, pipx requires nox to create virtual environments with venv. nox currently uses virtualenv. pipx uses a fork of nox at https://github.com/cs01/nox on the branch cs01/use-venv until this is fixed in nox. See https://github.com/theacodes/nox/issues/199
</details>

This will create virtual environments for each nox "session" in the `.nox` folder. If you want to run specific sessions, you can pass the `--session` argument to `nox`. To list sessions, pass `--list`.

## Documentation

Documentation has a couple steps to it. The first step is to generate markdown files that contain the current pipx API and fill in various templates (see `templates` directory). These files will have a header at the top indicating they were generated and shouldn't be manually modified.

The second is to compile the markdown files in `docs` with `mkdocs`.

Both of these steps are done in a single build command:
```
pipx run nox --session docs
```

To preview changes, including live reloading, run
```
.nox/docs-3-6/bin/mkdocs serve
```

If you make changes to the pipx cli api or any template, regenerate the `.md` files in the `docs` folder:
```
pipx run nox --session docs
```

### Publishing Changes to GitHub pages

```
pipx run nox --session docs
.nox/docs-3-6/bin/mkdocs serve
```
