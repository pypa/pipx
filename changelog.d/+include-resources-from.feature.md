Rename `--include-apps-from` to `--include-resources-from` and the manifest key to match. The option always exposed
manual pages and shell completions alongside apps, so the new name describes what it does; `--include-apps` keeps its
name. A venv recorded under the old key is migrated on read.
