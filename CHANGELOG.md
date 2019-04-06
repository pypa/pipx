0.13.0.0
* Add `runpip` command to run arbitrary pip commands in pipx-managed virtual environments
* Do not raise error when running `pipx install PACKAGE` and the package has already been installed by pipx (#125). This is the cause of the major version change from 0.12 to 0.13.
* Add `--skip` argument to `upgrade-all` and `reinstall-all` commands, to let the user skip particular packages

0.12.3.3
* Update logic in determining a package's binaries during installation. This removes spurious binaries from the installation. (#104)
* Improve compatibility with Debian distributions by using `shutil.which` instead of `distutils.spawn.find_executable` (#102)

0.12.3.2
* Fix infinite recursion error when installing package such as `cloudtoken==0.1.84` (#103)
* Fix windows type errors (#96, #98)

0.12.3.1
* Fix "WindowsPath is not iterable" bug

0.12.3.0
* Add `--include-deps` argument to include binaries of dependent packages when installing with pipx. This improves compatibility with packages that depend on other installed packages, such as `jupyter`.
* Speed up `pipx list` output (by running multiple processes in parallel) and by collecting all metadata in a single subprocess call
* More aggressive cache directory removal when `--no-cache` is passed to `pipx run`
* [dev] Move inline text passed to subprocess calls to their own files to enable autoformating, linting, unit testing

0.12.2.0
* Add support for PEP 582's `__pypackages__` (experimental). `pipx run BINARY` will first search in `__pypackages__` for binary, then fallback to installing from PyPI. `pipx run --pypackages BINARY` will raise an error if the binary is not found in `__pypackages__`.
* Fix regression when installing with `--editable` flag (#93)
* [dev] improve unit tests

0.12.1.0
* Cache and reuse temporary Virtual Environments created with `pipx run` (#61)
* Update binary discovery logic to find "scripts" like awscli (#91)
* Forward `--pip-args` to the pip upgrade command (previously the args were forwarded to install/upgrade commands for packages) (#77)
* When using environment variable PIPX_HOME, Virtual Environments will now be created at `$PIPX_HOME/venvs` rather than at `$PIPX_HOME`.
* [dev] refactor into multiple files, add more unit tests

0.12.0.4
* Fix parsing bug in pipx run

0.12.0.3
* list python2 as supported language so that pip installs with python2 will no longer install the pipx on PyPI from the original pipx owner. Running pipx with python2 will fail, but at least it will not be as confusing as running the pipx package from the original owner.

0.12.0.2
* forward arguments to run command correctly #90

0.12.0.1
* stop using unverified context #89

0.12.0.0
* Change installation instructions to use `pipx` PyPI name
* Add `ensurepath` command

0.11.0.2
 * add version argument parsing back in (fixes regression)

0.11.0.1
 * add version check, command check, fix printed version update installation instructions

0.11.0.0
* Replace `pipx BINARY` with `pipx run BINARY` to run a binary in an ephemeral environment. This is a breaking API change so the major version has been incremented. (Issue #69)
* upgrade pip when upgrading packages (Issue #72)
* support --system-site-packages flag (Issue #64)

0.10.4.1
* Fix version printed when `pipx --version` is run

0.10.4.0
* Add --index-url, --editable, and --pip-args flags
* Updated README with pipsi migration instructions

0.10.3.0
* Display python version in list
* Do not reinstall package if already installed (added `--force` flag to override)
* When upgrading all packages, print message only when package is updated
* Avoid accidental execution of pipx.__main__
