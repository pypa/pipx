import nox

# NOTE: these tests require nox to create virtual environments
# with venv. nox currently uses virtualenv. pipx
# uses a fork of nox at https://github.com/cs01/nox
# on the branch cs01/use-venv
# To invoke nox for pipx, use:
# pipx run --spec=git+https://github.com/cs01/nox.git@2ba8984a nox
# until this is fixed in nox. See
# https://github.com/theacodes/nox/issues/199

python = ["3.6"]


@nox.session(python=python)
def unittests(session):
    session.install(".")
    session.run("python", "-m", "unittest", "discover")


@nox.session(python=python)
def lint(session):
    session.install(".[dev]")
    files = ["pipx", "tests"]
    session.run("black", "--check", *files)
    session.run("flake8", *files)
    session.run("mypy", *files)
    session.run("check-manifest")
    session.run("python", "setup.py", "check", "--metadata", "--strict")


@nox.session(python=python)
def docs(session):
    session.install(".[docs]")
    session.run("python", "generate_docs.py")
    session.run("mkdocs", "build")
