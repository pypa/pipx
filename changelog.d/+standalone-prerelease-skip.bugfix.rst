``pipx`` no longer treats a python-build-standalone prerelease build (such as ``3.16.0a1``) as its stable
version; fetching a Python that only has prerelease builds fails with a clear message instead of silently
installing an alpha.
