Stop ``pipx run`` from retrying a failed uv install with pip. A venv directory without ``pipx_metadata.json`` no longer
counts as recorded with the pip backend, so it resolves its backend like a new venv, and a ``pipx run`` whose install
fails now expires its cache entry so the next run rebuilds it. pip ignores ``UV_INDEX_URL``, so the retry fetched the
package from pip's default index instead of the private one.
