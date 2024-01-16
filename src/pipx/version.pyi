version: str
version_tuple: tuple[int, int, int, str, str] | tuple[int, int, int]

# Note that newer versions of setuptools_scm also add __version__, but we are
# not forcing new versions of setuptools_scm, so only these imports are allowed.
