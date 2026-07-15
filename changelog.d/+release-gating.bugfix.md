Gate a PyPI release on the test suite and validate the built artifacts before publishing. The release workflow now runs
the full test matrix for the tagged commit, checks the distributions with `twine`, and confirms the built version
matches the tag, so a broken build or a mismatched tag cannot reach PyPI.
