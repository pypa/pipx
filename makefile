.PHONY: test docs develop build publish publish_docs lint

develop:
	pipx run nox -s develop

lint:
	pipx run nox -s lint

test:
	pipx run nox

publish:
	pipx run nox -s publish-3.7

docs:
	pipx run nox -s docs-3.7 -r

watch_docs:
	pipx run nox -s watch_docs-3.7 -r

publish_docs:
	pipx run nox -s publish_docs-3.7 -r
