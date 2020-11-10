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
    "isort",
]
# Packages whose dependencies need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
#
# BREAK[version] == Always breaks for specific version or all versions
# Pre[version] == Works with prebuilt wheels for specific version or all versions
#
# PACKAGE               WIN             MACOS               UNIX
#                       Pre/BREAK       Pre/BREAK           Pre/BREAK
# ----------------------------------------------------------------------
# ansible==2.9.13       BREAK           .
# beancount==2.3.3      BREAK            BREAK3.9
# black==20.8b1         .               .
# coala==0.11.0         BREAK3.7
# gdbgui==0.14.0.1      .               Pre3.9
# gns3-gui==2.2.15      .               Pre3.[67]
# grow==1.0.0a10        .               Pre3.[67]
# howdoi==2.0.7         .                BREAK3.9
# hyde==0.8.9           .                BREAK3.9
# jupyter==1.0.0        .               Pre
# kibitzr==6.0.0        .                BREAK3.9
# klaus=1.5.2           BREAK           .
# lektor==3.2.0         .               Pre3.[67]
# mackup==0.8.29        BREAK3.7        .
# mayan-edms==3.5.2     .                BREAK3.9
# nikola==8.1.1         .               Pre3.[67]/BREAK3.9
# weblate==4.3.1        BREAK           Pre3.[678]/BREAK3.9
# ----------------------------------------------------------------------

PREBUILD_PACKAGES = {
    "all": ["jupyter==1.0.0"],
    "macos": ["black==20.8b1"],
    "unix": [],
    "win": [],
}


def prebuild_wheels(session, prebuild_dict):
    if sys.platform == "darwin":
        platform = "macos"
    elif sys.platform == "win32":
        platform = "win"
    else:
        platform = "unix"

    prebuild_list = PREBUILD_PACKAGES.get("all", []) + PREBUILD_PACKAGES.get(
        platform, []
    )

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
    session.install("-U", "pip")
    session.install("-e", ".", "pytest")
    tests = session.posargs or ["tests"]
    session.run("pytest", "-m", "all_packages", *tests)


@nox.session
def cover(session):
    """Coverage analysis"""
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session(python=PYTHON_DEFAULT)
def lint(session):
    session.install(*LINT_DEPENDENCIES)
    files = [str(Path("src") / "pipx"), "tests", "scripts"] + [
        str(p) for p in Path(".").glob("*.py")
    ]
    session.run("isort", "--check", "--diff", "--profile", "black", *files)
    session.run("black", "--check", *files)
    session.run("flake8", *files)
    session.run("mypy", *files)
    session.run("check-manifest")
    session.run("python", "setup.py", "check", "--metadata", "--strict")


@nox.session(python=PYTHON_DEFAULT)
def docs(session):
    session.install(*DOC_DEPENDENCIES)
    session.env[
        "PIPX__DOC_DEFAULT_PYTHON"
    ] = "typically the python used to execute pipx"
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


def on_master_no_changes(session):
    if has_changes():
        session.error("All changes must be committed or removed before publishing")
    branch = get_branch()
    if branch != "master":
        session.error(f"Must be on 'master' branch. Currently on {branch!r} branch")


@nox.session(python="3.8")
def publish(session):
    on_master_no_changes(session)
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


@nox.session(python="3.8")
def pre_release(session):
    on_master_no_changes(session)
    if session.posargs:
        new_version = session.posargs[0]
    else:
        new_version = input("Enter new version: ")
    session.run("python", "scripts/pipx_prerelease.py", new_version)
    session.run("git", "--no-pager", "diff", external=True)
    print("")
    session.log(
        "If `git diff` above looks ok, execute the following command:\n\n"
        f"    git commit -a -m 'Pre-release {new_version}.'\n"
    )


@nox.session(python="3.8")
def post_release(session):
    on_master_no_changes(session)
    session.run("python", "scripts/pipx_postrelease.py")
    session.run("git", "--no-pager", "diff", external=True)
    print("")
    session.log(
        "If `git diff` above looks ok, execute the following command:\n\n"
        "    git commit -a -m 'Post-release.'\n"
    )
