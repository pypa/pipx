.PHONY: test docs develop build publish publish_docs

develop:
	pipx run --spec=git+https://github.com/cs01/nox.git@7f65d2abc nox -f automation.py -s develop

test:
	# TODO use `pipx run nox` when nox supports venv creation (and thus
	# pipx tests pass)
	pipx run --spec=git+https://github.com/cs01/nox.git@7f65d2abc nox

publish:
	pipx run nox -f automation.py -s publish-3.6

docs:
	pipx run nox --session docs -s docs-3.6

watch_docs:
	pipx run nox -f automation.py -s watch_docs-3.6

publish_docs:
	pipx run nox -f automation.py -s publish_docs-3.6
