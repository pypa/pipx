Reject a `--suffix` that contains anything but letters, digits, and the characters `.` `_` `-` `+` `@`. A suffix is
spliced straight into the names of the links pipx writes into `PIPX_BIN_DIR` and `PIPX_MAN_DIR`, so a value such as
`/../../owned` could previously place those links outside pipx's own directories.
