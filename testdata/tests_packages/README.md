# Introduction

`primary_packages.txt` is the master list, containing all packages installed or injected in the pipx tests `tests`.
Platform-specific list files listing both these primary packages and their dependencies are generated from it. These
platform-specific list files are used to populate the directory `.pipx_tests/package_cache`.

# Generating the platform-specific lists from the master list

Make sure that `primary_packages.txt` lists every package and version the tests install or inject, then on each target
platform execute:

- `python scripts/list_test_packages.py testdata/tests_packages/primary_packages.txt testdata/tests_packages`

# Updating / Populating the directory `.pipx_tests/package_cache` before running the tests

Pre-populating this directory allows the pipx `tests` to run completely offline.

Execute from the top-level pipx repo directory:

- `mkdir -p .pipx_tests/package_cache`
- `python3 scripts/update_package_cache.py testdata/tests_packages .pipx_tests/package_cache`
