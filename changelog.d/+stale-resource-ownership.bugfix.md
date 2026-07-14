Remove a dropped app or man page during upgrade only when pipx still owns the exposed file, so a command a user or
another package replaced is left in place.
