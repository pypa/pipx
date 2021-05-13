`tests_primary_packages.txt` is the master list, and platform specific files
are generated from it.  For a given system and python version, these files list
all of the packages necessary to install all of the pipx tests `tests`.

To generate these lists:
* Make sure that the file in this directory `tests_primary_packages.txt` is up to date for every package & version that is installed or injected in the tests.
* Manually activate the Github workflow: Create tests package lists for offline tests
* Download the artifact `lists` and put the files from it into this directory.

To locally generate these lists, on the target platform execute:
    nox -s create_test_package_list
