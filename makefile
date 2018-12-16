.PHONY: build publish


windows_shell:
	docker build -t pipx_windows docker/windows
	docker run -v "`pwd`:/src/" -it pipx_windows /bin/bash
	# docker run -v "`pwd`:/src/" pipx_windows

build:
	python -m pip install --upgrade --quiet setuptools wheel twine
	python setup.py --quiet sdist bdist_wheel

publish:
	python -m twine upload dist/*

clean:
	rm -r build dist
