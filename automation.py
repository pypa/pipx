import nox


python = ["3.6"]


@nox.session(python=["3.6", "3.7"])
def develop(session):
    session.install("-e", ".", ".[dev]", ".[docs]")


@nox.session(python=python)
def build(session):
    session.install("setuptools")
    session.install("wheel")
    session.install("twine")
    session.run("python", "setup.py", "--quiet", "sdist", "bdist_wheel")


@nox.session(python=python)
def publish(session):
    build(session)
    print("REMINDER: Has the changelog been updated?")
    session.run("python", "-m", "twine", "upload", "dist/*")


@nox.session(python=python)
def publish_docs(session):
    session.install(".[docs]")
    session.run("python", "generate_docs.py")
    session.run("mkdocs", "gh-pages")
