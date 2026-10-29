``pipx run`` now keys its cache on the absolute path of a local ``--spec``, ``--with`` or ``--find-links`` value. The
same relative path typed in two directories, such as ``--spec ./dist/tool-1.0-py3-none-any.whl``, shared one
environment, so the second directory ran the first directory's build.
