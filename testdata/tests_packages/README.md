# Introduction

`tests_primary_packages.txt` is the master list, containing all packages
installed or injected in the pipx tests `tests`.  Platform-specific list files
listing both these primary packages and their dependencies are generated from
it.  These platform-specific list files are used to populate the directory
`.pipx_tests/package_cache`.

# Generating the platform-specific lists from the master list

* Make sure that the file in this directory `tests_primary_packages.txt` is up to date for every package & version that is installed or injected in the tests.
* Manually activate the Github workflow: Create tests package lists for offline tests
* Download the artifact `lists` and put the files from it into this directory.

To locally generate these lists, on the target platform execute:
    nox -s create_test_package_list

# Updating / Populating the directory `.pipx_tests/package_cache` before running the tests
* execute `nox -s refresh_packages_cache`

Or manually execute:
* `mkdir -p .pipx_tests/package_cache`
* `python3 scripts/update_package_cache.py testdata/tests_packages .pipx_tests/package_cache`
