.PHONY: test docs develop build publish publish_docs

develop:
	pipx run nox --noxfile automation.py -s develop-3.6

docs:
	pipx run nox --session docs

test:
	# TODO use `pipx run nox` when nox supports venv creation (and thus
	# pipx tests pass)
	pipx run --spec=git+https://github.com/cs01/nox.git@7f65d2abc nox

publish:
	pipx run nox --noxfile automation.py -s publish-3.6

publish_docs:
	pipx run nox --noxfile automation.py -s publish_docs-3.6
