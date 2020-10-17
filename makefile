.PHONY: test docs develop build publish publish_docs lint

develop:
	pipx run nox -s develop

lint:
	pipx run nox -s lint

test:
	pipx run nox

publish:
	pipx run nox -s publish

docs:
	pipx run nox -s docs -r

watch_docs:
	pipx run nox -s watch_docs -r

publish_docs:
	pipx run nox -s publish_docs -r
