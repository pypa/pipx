``pipx uninject`` no longer removes a dependency the main package always needs, such as one marked
``extra != "cli"``, when that package declares extras, and ``pipx install --include-deps`` with an extra now exposes
the apps of such a dependency.
