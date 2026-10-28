pipx no longer crashes on Python 3.11 and 3.12 when a package's ``installed-files.txt`` lists a looping symlink, and
skips that entry instead.
