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
