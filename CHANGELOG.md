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
