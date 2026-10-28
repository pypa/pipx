Read a package name from a local ``pyproject.toml`` or wheel only for local path specs. A URL spec such as
``https://host/app.whl`` no longer takes its name, and with it the target environment, from a file at the matching
relative path below the working directory.
