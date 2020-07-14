.PHONY: test docs develop build publish publish_docs lint

develop:
	pipx run --spec=git+https://github.com/cs01/nox.git@5ea70723e9e6 nox -s develop

lint:
	pipx run nox -s lint

test:
	# TODO use `pipx run nox` when nox supports venv creation (and thus
	# pipx tests pass)
	pipx run --spec=git+https://github.com/cs01/nox.git@5ea70723e9e6 nox

publish:
	pipx run nox -s publish-3.7

docs:
	pipx run nox -s docs-3.7 -r

watch_docs:
	pipx run nox -s watch_docs-3.7 -r

publish_docs:
	pipx run nox -s publish_docs-3.7 -r
