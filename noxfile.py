import subprocess
import sys
from pathlib import Path

import nox  # type: ignore

PYTHON_ALL = ["3.6", "3.7", "3.8", "3.9"]
PYTHON_DEFAULT = "3.8"

if sys.platform == "win32":
    # docs fail on Windows, even if `chcp.com 65001` is used
    nox.options.sessions = ["tests", "lint"]
else:
    nox.options.sessions = ["tests", "lint", "docs"]

nox.options.reuse_existing_virtualenvs = True

DOC_DEPENDENCIES = [".", "jinja2", "mkdocs", "mkdocs-material"]
LINT_DEPENDENCIES = [
    "black==19.10b0",
    "flake8",
    "flake8-bugbear",
    "mypy",
    "check-manifest",
    "packaging>=20.0",
]
# Packages that need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
# PREBUILD_PACKAGES = ["jupyter==1.0.0", "black==20.8b1"]
PREBUILD_PACKAGES = ["jupyter==1.0.0"]


def prebuild_wheels(session, prebuild_list):
    session.install("wheel")
    wheel_dir = Path(session.virtualenv.location) / "prebuild_wheels"
    wheel_dir.mkdir(exist_ok=True)

    for prebuild in prebuild_list:
        session.run("pip", "wheel", f"--wheel-dir={wheel_dir}", prebuild, silent=True)


@nox.session(python=PYTHON_ALL)
def tests(session):
    prebuild_wheels(session, PREBUILD_PACKAGES)
    session.install("-e", ".", "pytest", "pytest-cov")
    tests = session.posargs or ["tests"]
    session.run(
        "pytest", "--cov=pipx", "--cov-report=", "-m", "not all_packages", *tests
    )
    session.notify("cover")


@nox.session(python=PYTHON_ALL)
def test_all_packages(session):
    prebuilds = PREBUILD_PACKAGES.copy()
    prebuilds.extend(
        ["lektor==3.2.0", "gdbgui==0.14.0.1", "gns3-gui==2.2.15", "grow==1.0.0a10"]
    )
    if session.python != "3.9":
        # Fail to build under py3.9 (2020-10-29)
        prebuilds.extend(["weblate==4.3.1", "nikola==8.1.1"])
    prebuild_wheels(session, prebuilds)
    session.install("-e", ".", "pytest", "pytest-cov")
    tests = session.posargs or ["tests"]
    session.run("pytest", "--cov=pipx", "--cov-report=", "-m", "all_packages", *tests)
    session.notify("cover")


@nox.session
def cover(session):
    """Coverage analysis"""
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session(python=PYTHON_DEFAULT)
def lint(session):
    session.install(*LINT_DEPENDENCIES)
    files = [str(Path("src") / "pipx"), "tests"] + [
        str(p) for p in Path(".").glob("*.py")
    ]
    session.run("black", "--check", *files)
    session.run("flake8", *files)
    session.run("mypy", *files)
    session.run("check-manifest")
    session.run("python", "setup.py", "check", "--metadata", "--strict")


@nox.session(python=PYTHON_DEFAULT)
def docs(session):
    session.install(*DOC_DEPENDENCIES)
    session.run("python", "generate_docs.py")
    session.run("mkdocs", "build")


@nox.session(python=PYTHON_ALL)
def develop(session):
    session.install(*DOC_DEPENDENCIES, *LINT_DEPENDENCIES)
    session.install("-e", ".")


@nox.session(python=PYTHON_DEFAULT)
def build(session):
    session.install("setuptools")
    session.install("wheel")
    session.install("twine")
    session.run("rm", "-rf", "dist", "build", external=True)
    session.run("python", "setup.py", "--quiet", "sdist", "bdist_wheel")


def has_changes():
    status = (
        subprocess.run(
            "git status --porcelain", shell=True, check=True, stdout=subprocess.PIPE
        )
        .stdout.decode()
        .strip()
    )
    return len(status) > 0


def get_branch():
    return (
        subprocess.run(
            "git rev-parse --abbrev-ref HEAD",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
        )
        .stdout.decode()
        .strip()
    )


@nox.session(python=PYTHON_DEFAULT)
def publish(session):
    if has_changes():
        session.error("All changes must be committed or removed before publishing")
    branch = get_branch()
    if branch != "master":
        session.error(f"Must be on 'master' branch. Currently on {branch!r} branch")
    build(session)
    print("REMINDER: Has the changelog been updated?")
    session.run("python", "-m", "twine", "upload", "dist/*")


@nox.session(python=PYTHON_DEFAULT)
def watch_docs(session):
    session.install(*DOC_DEPENDENCIES)
    session.run("mkdocs", "serve")


@nox.session(python=PYTHON_DEFAULT)
def publish_docs(session):
    session.install(*DOC_DEPENDENCIES)
    session.run("python", "generate_docs.py")
    session.run("mkdocs", "gh-deploy")
