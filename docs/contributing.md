Thanks for your interest in contributing to pipx!

Everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise is expected to follow
the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).

## Running pipx From Source Tree
To run the pipx executable from your source tree during development, run pipx from the src directory:

```
python src/pipx --version
```

## Pre-commit
The use of [pre-commit](https://pre-commit.com/) is recommended.  It can show
all and fix some lint errors before commit, saving you the trouble of finding
out later that it failed CI Lint errors, and saving you from having to run `nox
-s lint` separately.

In the pipx git repository is a `.pre-commit-config.yaml` configuration file
tailored just for pipx and its lint requirements.  To use pre-commit in your
clone of the pipx repository, you need to do the following **one-time setup
procedure**:

1. Install pre-commit using `pipx install pre-commit`
2. In the top level directory of your clone of the pipx repository, execute `pre-commit install`

Afterwards whenever you commit in this repository, it will first run pipx's
personalized lint checks.  If it makes a fix to a file (e.g. using `black` or
`isort`), you will need to `git add` that file again before committing it
again.  If it can't fix your commit itself, it will tell you what's wrong, and
you can fix it manually before re-adding the edited files and committing again.

If for some reason you want to commit and skip running pre-commit, you can use
the switch `git commit --no-verify`.

## Running Tests

### Setup
pipx uses an automation tool called [nox](https://pypi.org/project/nox/) for development, continuous integration testing, and various tasks.

`nox` defines tasks or "sessions" in `noxfile.py` which can be run with `nox -s SESSION_NAME`. Session names can be listed with `nox -l`.

Install nox for pipx development:
```
python -m pip install --user nox
```

Tests are defined as `nox` sessions. You can see all nox sessions with
```
nox -l
```

At the time of this writing, the output looks like this
```
- refresh_packages_cache-3.6 -> Populate .pipx_tests/package_cache
- refresh_packages_cache-3.7 -> Populate .pipx_tests/package_cache
- refresh_packages_cache-3.8 -> Populate .pipx_tests/package_cache
- refresh_packages_cache-3.9 -> Populate .pipx_tests/package_cache
- tests_internet-3.6 -> Tests using internet pypi only
- tests_internet-3.7 -> Tests using internet pypi only
- tests_internet-3.8 -> Tests using internet pypi only
- tests_internet-3.9 -> Tests using internet pypi only
* tests-3.6 -> Tests using local pypiserver only
* tests-3.7 -> Tests using local pypiserver only
* tests-3.8 -> Tests using local pypiserver only
* tests-3.9 -> Tests using local pypiserver only
- test_all_packages-3.6
- test_all_packages-3.7
- test_all_packages-3.8
- test_all_packages-3.9
- cover -> Coverage analysis
* lint
- develop-3.6
- develop-3.7
- develop-3.8
- develop-3.9
- build
- publish
* build_docs
- publish_docs
- watch_docs
- pre_release
- post_release
- create_test_package_list-3.6
- create_test_package_list-3.7
- create_test_package_list-3.8
- create_test_package_list-3.9
```

### Unit Tests
To run unit tests in Python3.9, you can run
```
nox -s tests-3.9
```

!!! tip
    You can run a specific unit test by passing arguments to pytest, the test runner pipx uses:

    ```
    nox -s tests-3.8 -- -k EXPRESSION
    ```

    `EXPRESSION` can be a test name, such as

    ```
    nox -s tests-3.8 -- -k test_uninstall
    ```

    Coverage errors can usually be ignored when only running a subset of tests.

### Running Unit Tests Offline

Running the unit tests requires a directory `.pipx_tests/package_cache` to be
populated from a fixed list of package distribution files (wheels or source
files).  If you have network access, `nox -s tests` automatically makes sure
this directory is populated (including downloading files if necessary) as a
first step.  Thus if you are running the tests with network access, you can
ignore the rest of this section.

If, however, you wish to run tests offline without the need for network access,
you can populate `.pipx_tests/package_cache` yourself manually beforehand when
you do have network access.

#### Populating the cache directory using nox
To populate `.pipx_tests/package_cache` manually using nox, execute:
```
nox -s refresh_packages_cache
```
This will sequence through available python executable versions to populate the
cache directory for each version of python on your platform.

#### Populating the cache directory without nox
An alternate method to populate `.pipx_tests/package_cache` without nox is to
execute:
```
mkdir -p .pipx_tests/package_cache
python3 scripts/update_package_cache.py testdata/tests_packages .pipx_tests/package_cache
```
You must do this using every python version that you wish to use to run the
tests.

### Lint Tests

```
nox -s lint
```

### Installing or injecting new packages in tests
If the tests are modified such that a new package / version combination is
`pipx install`ed or `pipx inject`ed that wasn't used in other tests, then one
must make sure it's added properly to the packages lists in
`testdata/tests_packages`.

To accomplish this:
* Edit `testdata/tests_packages/primary_packages.txt` to add the new package(s) that you wish to `pipx install` or `pipx inject` in the tests.

Then using Github workflows to generate all platforms in the Github CI:
* Manually activate the Github workflow: Create tests package lists for offline tests
* Download the artifact `lists` and put the files from it into `testdata/tests_packages/`

Or to locally generate these lists from `testdata/tests_packages/primary_packages.txt`, on the target platform execute:
* `nox -s create_test_package_list`

Finally, check-in the new or modified list files in the directory `testdata/tests_packages`

## Testing pipx on Continuous Integration builds
When you push a new git branch, tests will automatically be run against your code as defined in `.github/workflows/on-push.yml`.

## Building Documentation

`pipx` autogenerates API documentation, and also uses templates.

When updating pipx docs, make sure you are either modifying a file in the `templates` directory, or the `docs` directory. If in the `docs` directory, make sure the file was not autogenerated from the `templates` directory. Autogenerated files have a note at the top of the file.

You can generate the documentation with
```
nox -s build_docs
```

This will capture CLI documentation for any pipx argument modifications, as well as generate templates to the docs directory.

To preview changes, including live reloading, open another terminal and run
```
nox -s watch_docs
```

### Publishing Doc Changes to GitHub pages
```
nox -s publish_docs
```

## Releasing New `pipx` Versions
### Pre-release

First, make sure the changelog is complete.  Next decide what the next version
number will be.  Then, from a clone of the main pypa pipx repo (not a
fork) execute:
```
nox -s pre_release
```

Enter the new version number when asked. When the script is finished, check the
diff it produces.  If the diff looks correct, commit the changes as the
script instructs, and push the result.

The script will modify `src/pipx/version.py` to contain the new version, and
also update the changelog (`docs/changelog.md`) to specify the new version.

### Release
To publish to PyPI simply create a "published" release on Github.  This will
trigger Github workflows that both publish the pipx version to PyPI and publish
the pipx documentation to the pipx website.

### Post-release
From a clone of the main pypa pipx repo (not a
fork) execute:
```
nox -s post_release
```

When the script is finished, check the diff it produces.  If the diff looks
correct, commit the changes as the script instructs, and push the result.

This will update pipx's version in `src/pipx/version.py` by adding a suffix
`"dev0"` for unreleased development, and will update the changelog to start a
new section at the top entitled `dev`.
