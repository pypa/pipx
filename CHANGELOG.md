## dev

- [docs] Make the logo more visible in dark mode

## 1.3.2

- The project version number is now dynamic and generated from the VCS at build time
- [docs] Add additonal example for --pip-args option, to docs/examples.md

## 1.3.1

- Fix combining of --editable and --force flag

## 1.3.0

- Check whether pip module exists in shared lib before performing any actions, such as `reinstall-all`.
- Drop `setuptools` and `wheel` from the shared libraries. This results in less time consumption when the libraries are
  automatically upgraded.
- Allow running `pip` with `pipx run`
- Support PEP 723 run requirements in `pipx run`.
- Imply `--include-apps` when running `pipx inject --include-deps`
- Add `--with-suffix` for `pipx inject` command
- `pipx install`: emit a warning when `--force` and `--python` were passed at the same time
- Drop support for Python 3.7
- Make usage message in `pipx run` show `package_or_url`, so extra will be printed out as well
- Add `--force-reinstall` to pip arguments when `--force` was passed
- Use the py launcher, if available, to select Python version with the `--python` option
- Support including requirements in scripts run using `pipx run` (#916)
- Pass `pip_args` to `shared_libs.upgrade()`
- Fallback to user's log path if the default log path (`$PIPX_HOME/logs`) is not writable to aid with pipx being used
  for multi-user (e.g. system-wide) installs of applications
- Fix wrong interpreter usage when injecting local pip-installable dependencies into venvs
- add pre-commit hook support
- Don't show escaped backslashes for paths in console output
- Move `pipx` paths to ensure compatibility with the platform-specific user directories
- [docs] Add more examples for `pipx run`
- [docs] Add subsection to make README easier to read
- Add `pipx install --preinstall` to support preinstalling build requirements
- Pass `--no-input` to pip when output is not piped to parent stdout
- Fix program name in generated manual page
- Print all environment variables in `pipx environment`
- Return an error message when directory can't be added to PATH successfully
- Expose manual pages included in an application installed with `pipx install`
- Add explicit 3.12 support

## 1.2.1

- Fix compatibility to packaging 23.2+ by removing reliance on packaging's requirement validation logic and detecting a
  URL-based requirement in pipx. (#1070)

## 1.2.0

- Add test for pip module in `pipx reinstall` to fix an issue with `pipx reinstall-all` (#935)
- Add `pipx uninject` command (#820)
- [docs] Fix `pipx run` examples and update Python versions used by `pipx install` examples
- [docs] Add an example for installation from source with extras
- Match pip's behaviour when package name ends with archive extension (treat it as a path)
- Ship a [zipapp](https://docs.python.org/3/library/zipapp.html) of pipx
- Change the program name to `path/to/python -m pipx` when running as `python -m pipx`
- Improve the detection logic for MSYS2 to avoid entering infinite loop (#908) (#938)
- Remove extra trailing quote from exception message
- Fix EncodingWarning in `pipx_metadata_file`.

## 1.1.0

- Fix encoding issue on Windows when pip fails to install a package
- Improve the behaviour of `shlex.split` on Windows, so paths on Windows can be handled properly when they are passed in
  `--pip-args`. (#794)
- Add `pipx environment` command (#793)
- Add `list --short` option to list only package names (#804)
- [docs] Fix the command for
  [installing development version](https://pipx.pypa.io/stable/installation/#install-pipx-development-versions). (#801)
- [docs] Fix test status badge in readme file
- [docs] Add more examples
- [dev] Change github action job names
- [docs] Add additional examples for installation from git repos
- [packaging] Switch to [PEP 621](https://www.python.org/dev/peps/pep-0621/)
- Add a CACHEDIR.TAG to the cache directory to prevent it from being included in archives and backups. For more
  information about cache directory tags, see https://bford.info/cachedir

## 1.0.0

- Support [argcomplete 2.0.0](https://pypi.org/project/argcomplete/2.0.0) (#790)
- Include machinery to build a manpage for pipx with [argparse-manpage](https://pypi.org/project/argparse-manpage/).
- Add better handling for 'app not found' when a single app is present in the project, and an improved error message
  (#733)
- Fixed animations sending output to stdout, which can break JSON output. (#769)
- Fix typo in `pipx upgrade-all` output

## 0.17.0

- Support `pipx run` with version constraints and extras. (#697)

## 0.16.5

- Fixed `pipx list` output phrasing to convey that python version displayed is the one with which package was installed.
- Fixed `pipx install` to provide return code 0 if venv already exists, similar to pip’s behavior. (#736)
- [docs] Update ansible's install command in
  [Programs to Try document](https://pipx.pypa.io/stable/programs-to-try/#ansible) to work with Ansible 2.10+ (#742)

## 0.16.4

- Fix to `pipx ensurepath` to fix behavior in user locales other than UTF-8, to fix #644. The internal change is to use
  userpath v1.6.0 or greater. (#700)
- Fix virtual environment inspection for Python releases that uses an int for its release serial number. (#706)
- Fix PermissionError in windows when pipx manages itself. (#718)

## 0.16.3

- Organization: pipx is extremely pleased to now be a project of the Python Packaging Authority (PyPA)! Note that our
  github URL has changed to [pypa/pipx](https://github.com/pypa/pipx)
- Fixed `pipx list --json` to return valid json with no venvs installed. Previously would return an empty string to
  stdout. (#681)
- Changed `pipx ensurepath` bash behavior so that only one of {`~/.profile`, `~/.bash\_profile`} is modified with the
  extra pipx paths, not both. Previously, if a `.bash_profile` file was created where one didn't exist, it could cause
  problems, e.g. #456. The internal change is to use userpath v1.5.0 or greater. (#684)
- Changed default nox tests, Github Workflow tests, and pytest behavior to use local pypi server with fixed lists of
  available packages. This allows greater test isolation (no network pypi access needed) and determinism (fixed
  available dependencies.) It also allows running the tests offline with some extra preparation beforehand (See
  [Running Unit Tests Offline](https://pipx.pypa.io/stable/contributing/#running-unit-tests-offline)). The old style
  tests that use the internet to access pypi.org are still available using `nox -s tests_internet` or
  `pytest --net-pypiserver tests`. (#686)

* Colorama is now only installed on Windows. (#691)

## 0.16.2.1

- Changed non-venv-info warnings and notices from `pipx list` to print to stderr. This especially prevents
  `pipx list --json` from printing invalid json to stdout. (#680)
- Fixed bug that could cause uninstall on Windows with injected packages to uninstall too many apps from the local
  binary directory. (#679)

## 0.16.2.0

- Fixed bug #670 where uninstalling a venv could erroneously uninstall other apps from the local binary directory.
  (#672)
- Added `--json` switch to `pipx list` to output rich json-metadata for all venvs.
- Ensured log files are utf-8 encoded to prevent Unicode encoding errors from occurring with emojis. (#646)
- Fixed issue which made pipx incorrectly list apps as part of a venv when they were not installed by pipx. (#650)
- Fixed old regression that would prevent pipx uninstall from cleaning up linked binaries if the venv was old and did
  not have pipx metadata. (#651)
- Fixed bugs with suffixed-venvs on Windows. Now properly summarizes install, and actually uninstalls associated
  binaries for suffixed-venvs. (#653)
- Changed venv minimum python version to 3.6, removing python 3.5 which is End of Life. (#666)

## 0.16.1.0

- Introduce the `pipx.run` entry point group as an alternative way to declare an application for `pipx run`.
- Fix cursor show/hide to work with older versions of Windows. (#610)
- Support text colors on Windows. (#612)
- Better platform unicode detection to avoid errors and allow showing emojis when possible. (#614)
- Don't emit show cursor or hide cursor codes if STDERR is not a tty. (#620)
- Sped up `pipx list` (#624).
- pip errors no longer stream to the shell when pip fails during a pipx install. pip's output is now saved to a log
  file. In the shell, pipx will tell you the location of the log file and attempt to summarize why pip failed. (#625)
- For `reinstall-all`, fixed bug where missing python executable would cause error. (#634)
- Fix regression which prevented pipx from working with pythonloc (and `__pypackages__` folder). (#636)

## 0.16.0.0

- New venv inspection! The code that pipx uses to examine and determine metadata in an installed venv has been made
  faster, better, and more reliable. It now uses modern python libraries like `packaging` and `importlib.metadata` to
  examine installed venvs. It also now properly handles installed package extras. In addition, some problems pipx has
  had with certain characters (like periods) in package names should be remedied.
- Added reinstall command for reinstalling a single venv.
- Changed `pipx run` on non-Windows systems to actually replace pipx process with the app process instead of running it
  as a subprocess. (Now using python's `os.exec*`)
- [bugfix] Fixed bug with reinstall-all command when package have been installed using a specifier. Now the initial
  specifier is used.
- [bugfix] Override display of `PIPX_DEFAULT_PYTHON` value when generating web documentation for `pipx install` #523
- [bugfix] Wrap help documentation for environment variables.
- [bugfix] Fixed uninstall crash that could happen on Windows for certain packages
- [feature] Venv package name arguments now do not have to match exactly as pipx has them stored, but can be specified
  in any python-package-name-equivalent way. (i.e. case does not matter, and `.`, `-`, `_` characters are
  interchangeable.)
- [change] Venvs with a suffix: A suffix can contain any characters, but for purposes of uniqueness, python package name
  rules apply--upper- and lower-case letters are equivalent, and any number of `.`, `-`, or `_` characters in a row are
  equivalent. (e.g. if you have a suffixed venv `pylint_1.0A` you could not add another suffixed venv called
  `pylint--1-0a`, as it would not be a unique name.)
- [implementation detail] Pipx shared libraries (providing pip, setuptools, wheel to pipx) are no longer installed using
  pip arguments taken from the last regular pipx install. If you need to apply pip arguments to pipx's use of pip for
  its internal shared libraries, use PIP\_\* environment variables.
- [feature] Autocomplete for venv names is no longer restricted to an exact match to the literal venv name, but will
  autocomplete any logically-similar python package name (i.e. case does not matter, and `.`, `-`, `_` characters are
  all equivalent.)
- pipx now reinstall its internal shared libraries when the user executes `reinstall-all`.
- Made sure shell exit codes from every pipx command are correct. In the past some (like from `pipx upgrade`) were
  wrong. The exit code from `pipx runpip` is now the exit code from the `pip` command run. The exit code from
  `pipx list` will be 1 if one or more venvs have problems that need to be addressed.
- pipx now writes a log file for each pipx command executed to `$PIPX_HOME/logs`, typically `~/.local/pipx/logs`. pipx
  keeps the most recent 10 logs and deletes others.
- `pipx upgrade` and `pipx upgrade-all` now have a `--upgrade-injected` option which directs pipx to also upgrade
  injected packages.
- `pipx list` now detects, identifies, and suggests a remedy for venvs with old-internal data (internal venv names) that
  need to be updated.
- Added a "Troubleshooting" page to the pipx web documentation for common problems pipx users may encounter.
- pipx error, warning, and other messages now word-wrap so words are not split across lines. Their appearance is also
  now more consistent.

## 0.15.6.0

- [docs] Update license
- [docs] Display a more idiomatic command for registering completions on fish.
- [bugfix] Fixed regression in list, inject, upgrade, reinstall-all commands when suffixed packages are used.
- [bugfix] Do not reset package url during upgrade when main package is `pipx`
- Updated help text to show description for `ensurepath` and `completions` help
- Added support for user-defined default python interpreter via new `PIPX_DEFAULT_PYTHON`. Helpful for use with pyenv
  among other uses.
- [bugfix] Fixed bug where extras were ignored with a PEP 508 package specification with a URL.

## 0.15.5.1

- [bugfix] Fixed regression of 0.15.5.0 which erroneously made installing from a local path with package extras not
  possible.

## 0.15.5.0

- pipx now parses package specification before install. It removes (with warning) the `--editable` install option for
  any package specification that is not a local path. It also removes (with warning) any environment markers.
- Disabled animation when we cannot determine terminal size or if the number of columns is too small. (Fixes #444)
- [feature] Version of each injected package is now listed after name for `pipx list --include-injected`
- Change metadata recorded from version-specified install to allow upgrades in future. Adds pipx dependency on
  `packaging` package.
- [bugfix] Prevent python error in case where package has no pipx metadata and advise user how to fix.
- [feature] `ensurepath` now also ensures that pip user binary path containing pipx itself is in user's PATH if pipx was
  installed using `pip install --user`.
- [bugfix] For `pipx install`, fixed failure to install if user has `PIP_USER=1` or `user=true` in pip.conf. (#110)
- [bugfix] Requiring userpath v1.4.1 or later so ensure Windows bug is fixed for `ensurepath` (#437)
- [feature] log pipx version (#423)
- [feature] `--suffix` option for `install` to allow multiple versions of same tool to be installed (#445)
- [feature] pipx can now be used with the Windows embeddable Python distribution

## 0.15.4.0

- [feature] `list` now has a new option `--include-injected` to show the injected packages in the main apps
- [bugfix] Fixed bug that can cause crash when installing an app

## 0.15.3.1

- [bugfix] Workaround multiprocessing issues on certain platforms (#229)

## 0.15.3.0

- [feature] Use symlinks on Windows when symlinks are available

## 0.15.2.0

- [bugfix] Improved error reporting during venv metadata inspection.
- [bugfix] Fixed incompatibility with pypy as venv interpreter (#372).
- [bugfix] Replaced implicit dependency on setuptools with an explicit dependency on packaging (#339).
- [bugfix] Continue reinstalling packages after failure
- [bugfix] Hide cursor while pipx runs
- [feature] Add environment variable `USE_EMOJI` to allow enabling/disabling emojis (#376)
- [refactor] Moved all commands to separate files within the commands module (#255).
- [bugfix] Ignore system shared libraries when installing shared libraries pip, wheel, and setuptools. This also fixes
  an incompatibility with Debian/Ubuntu's version of pip (#386).

## 0.15.1.3

- [bugfix] On Windows, pipx now lists correct Windows apps (#217)
- [bugfix] Fixed a `pipx install` bug causing incorrect python binary to be used when using the optional --python
  argument in certain situations, such as running pipx from a Framework python on macOS and specifying a non-Framework
  python.

## 0.15.1.2

- [bugfix] Fix recursive search of dependencies' apps so no apps are missed.
- `upgrade-all` now skips editable packages, because pip disallows upgrading editable packages.

## 0.15.1.1

- [bugfix] fix regression that caused installing with --editable flag to fail package name determination.

## 0.15.1.0

- Add Python 3.8 to PyPI classifier and travis test matrix
- [feature] auto-upgrade shared libraries, including pip, if older than one month. Hide all pip warnings that a new
  version is available. (#264)
- [bugfix] pass pip arguments to pip when determining package name (#320)

## 0.15.0.0

Upgrade instructions: When upgrading to 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all packages
to take advantage of the new persistent pipx metadata files introduced in this release. These metadata files store pip
specification values, injected packages, any custom pip arguments, and more in each main package's venv. You can do this
by running `pipx reinstall-all` or `pipx uninstall-all`, then reinstalling manually.

- `install` now has no `--spec` option. You may specify any valid pip specification for `install`'s main argument.
- `inject` will now accept pip specifications for dependency arguments
- Metadata is now stored for each application installed, including install options like `--spec`, and injected packages.
  This information allows upgrade, upgrade-all and reinstall-all to work properly even with non-pypi installed packages.
  (#222)
- `upgrade` options `--spec` and `--include-deps` were removed. Pipx now uses the original options used to install each
  application instead. (#222)
- `upgrade-all` options `--include-deps`, `--system-site-packages`, `--index-url`, `--editable`, and `--pip-args` were
  removed. Pipx now uses the original options used to install each application instead. (#222)
- `reinstall-all` options `--include-deps`, `--system-site-packages`, `--index-url`, `--editable`, and `--pip-args` were
  removed. Pipx now uses the original options used to install each application instead. (#222)
- Handle missing interpreters more gracefully (#146)
- Change `reinstall-all` to use system python by default for apps. Now use `--python` option to specify a different
  python version.
- Remove the PYTHONPATH environment variable when executing any command to prevent conflicts between pipx dependencies
  and package dependencies when pipx is installed via homebrew. Homebrew can use PYTHONPATH manipulation instead of
  virtual environments. (#233)
- Add printed summary after successful call to `pipx inject`
- Support associating apps with Python 3.5
- Improvements to animation status text
- Make `--python` argument in `reinstall-all` command optional
- Use threads on OS's without support for semaphores
- Stricter parsing when passing `--` argument as delimiter

## 0.14.0.0

- Speed up operations by using shared venv for `pip`, `setuptools`, and `wheel`. You can see more detail in the 'how
  pipx works' section of the documentation. (#164, @pfmoore)
- Breaking change: for the `inject` command, change `--include-binaries` to `--include-apps`
- Change all terminology from `binary` to `app` or `application`
- Improve argument parsing for `pipx run` and `pipx runpip`
- If `--force` is passed, remove existing files in PIPX_BIN_DIR
- Move animation to start of line, hide cursor when animating

## 0.13.2.3

- Fix regression when installing a package that doesn't have any entry points

## 0.13.2.2

- Remove unnecessary and sometimes incorrect check after `pipx inject` (#195)
- Make status text/animation reliably disappear before continuing
- Update animation symbols

## 0.13.2.1

- Remove virtual environment if installation did not complete. For example, if it was interrupted by ctrl+c or if an
  exception occurred for any reason. (#193)

## 0.13.2.0

- Add shell autocompletion. Also add `pipx completions` command to print instructions on how to add pipx completions to
  your shell.
- Un-deprecate `ensurepath`. Use `userpath` internally instead of instructing users to run the `userpath` cli command.
- Improve detection of PIPX_BIN_DIR not being on PATH
- Improve error message when an existing symlink exists in PIPX_BIN_DIR and points to the wrong location
- Improve handling of unexpected files in PIPX_HOME (@uranusjr)
- swap out of order logic in order to correctly recommend --include-deps (@joshuarli)
- [dev] Migrate from tox to nox

## 0.13.1.1

- Do not raise bare exception if no binaries found (#150)
- Update pipsi migration script

## 0.13.1.0

- Deprecate `ensurepath` command. Use `userpath append ~/.local/bin`
- Support redirects and proxies when downloading python files (i.e. `pipx run http://url/file.py`)
- Use tox for document generation and CI testing (CI tests are now functional rather than static tests on style and
  formatting!)
- Use mkdocs for documentation
- Change default cache duration for `pipx run` from 2 to 14 days

## 0.13.0.1

- Fix upgrade-all and reinstall-all regression

## 0.13.0.0

- Add `runpip` command to run arbitrary pip commands in pipx-managed virtual environments
- Do not raise error when running `pipx install PACKAGE` and the package has already been installed by pipx (#125). This
  is the cause of the major version change from 0.12 to 0.13.
- Add `--skip` argument to `upgrade-all` and `reinstall-all` commands, to let the user skip particular packages

## 0.12.3.3

- Update logic in determining a package's binaries during installation. This removes spurious binaries from the
  installation. (#104)
- Improve compatibility with Debian distributions by using `shutil.which` instead of `distutils.spawn.find_executable`
  (#102)

## 0.12.3.2

- Fix infinite recursion error when installing package such as `cloudtoken==0.1.84` (#103)
- Fix windows type errors (#96, #98)

## 0.12.3.1

- Fix "WindowsPath is not iterable" bug

## 0.12.3.0

- Add `--include-deps` argument to include binaries of dependent packages when installing with pipx. This improves
  compatibility with packages that depend on other installed packages, such as `jupyter`.
- Speed up `pipx list` output (by running multiple processes in parallel) and by collecting all metadata in a single
  subprocess call
- More aggressive cache directory removal when `--no-cache` is passed to `pipx run`
- [dev] Move inline text passed to subprocess calls to their own files to enable autoformatting, linting, unit testing

## 0.12.2.0

- Add support for PEP 582's `__pypackages__` (experimental). `pipx run BINARY` will first search in `__pypackages__` for
  binary, then fallback to installing from PyPI. `pipx run --pypackages BINARY` will raise an error if the binary is not
  found in `__pypackages__`.
- Fix regression when installing with `--editable` flag (#93)
- [dev] improve unit tests

## 0.12.1.0

- Cache and reuse temporary Virtual Environments created with `pipx run` (#61)
- Update binary discovery logic to find "scripts" like awscli (#91)
- Forward `--pip-args` to the pip upgrade command (previously the args were forwarded to install/upgrade commands for
  packages) (#77)
- When using environment variable PIPX_HOME, Virtual Environments will now be created at `$PIPX_HOME/venvs` rather than
  at `$PIPX_HOME`.
- [dev] refactor into multiple files, add more unit tests

## 0.12.0.4

- Fix parsing bug in pipx run

## 0.12.0.3

- list python2 as supported language so that pip installs with python2 will no longer install the pipx on PyPI from the
  original pipx owner. Running pipx with python2 will fail, but at least it will not be as confusing as running the pipx
  package from the original owner.

## 0.12.0.2

- forward arguments to run command correctly #90

## 0.12.0.1

- stop using unverified context #89

## 0.12.0.0

- Change installation instructions to use `pipx` PyPI name
- Add `ensurepath` command

## 0.11.0.2

- add version argument parsing back in (fixes regression)

## 0.11.0.1

- add version check, command check, fix printed version update installation instructions

## 0.11.0.0

- Replace `pipx BINARY` with `pipx run BINARY` to run a binary in an ephemeral environment. This is a breaking API
  change so the major version has been incremented. (Issue #69)
- upgrade pip when upgrading packages (Issue #72)
- support --system-site-packages flag (Issue #64)

## 0.10.4.1

- Fix version printed when `pipx --version` is run

## 0.10.4.0

- Add --index-url, --editable, and --pip-args flags
- Updated README with pipsi migration instructions

## 0.10.3.0

- Display python version in list
- Do not reinstall package if already installed (added `--force` flag to override)
- When upgrading all packages, print message only when package is updated
- Avoid accidental execution of pipx.**main**
