import subprocess
import sys
from pathlib import Path

import nox  # type: ignore

python = ["3.6", "3.7", "3.8", "3.9"]

if sys.platform == "win32":
    # docs fail on Windows, even if `chcp.com 65001` is used
    nox.options.sessions = ["tests", "lint"]
else:
    nox.options.sessions = ["tests", "lint", "docs"]

nox.options.reuse_existing_virtualenvs = True

doc_dependencies = [".", "jinja2", "mkdocs", "mkdocs-material"]
lint_dependencies = [
    "black==19.10b0",
    "flake8",
    "flake8-bugbear",
    "mypy",
    "check-manifest",
    "packaging>=20.0",
]
# Packages that need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
prebuild_packages = {"all": ["typed-ast", "pyzmq"], "darwin": ["argon2-cffi", "regex"]}


def prebuild_wheels(session, package_dict):
    session.install("wheel")
    wheel_dir = Path(session.virtualenv.location) / "prebuild_wheels"
    wheel_dir.mkdir(exist_ok=True)
    for platform in package_dict:
        if platform == "all" or platform == sys.platform:
            for prebuild_package in package_dict[platform]:
                session.run(
                    "pip",
                    "wheel",
                    f"--wheel-dir={wheel_dir}",
                    prebuild_package,
                    silent=True,
                )


@nox.session(python=python)
def tests(session):
    prebuild_wheels(session, prebuild_packages)
    session.install("-e", ".", "pytest", "pytest-cov")
    tests = session.posargs or ["tests"]
    session.run("pytest", "--cov=pipx", "--cov-report=", *tests)
    session.notify("cover")


@nox.session
def cover(session):
    """Coverage analysis"""
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session(python="3.8")
def lint(session):
    session.install(*lint_dependencies)
    files = [str(Path("src") / "pipx"), "tests"] + [
        str(p) for p in Path(".").glob("*.py")
    ]
    session.run("black", "--check", *files)
    session.run("flake8", *files)
    session.run("mypy", *files)
    session.run("check-manifest")
    session.run("python", "setup.py", "check", "--metadata", "--strict")


@nox.session(python="3.8")
def docs(session):
    session.install(*doc_dependencies)
    session.run("python", "generate_docs.py")
    session.run("mkdocs", "build")


@nox.session(python=python)
def develop(session):
    session.install(*doc_dependencies, *lint_dependencies)
    session.install("-e", ".")


@nox.session(python="3.8")
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


@nox.session(python="3.8")
def watch_docs(session):
    session.install(*doc_dependencies)
    session.run("mkdocs", "serve")


@nox.session(python="3.8")
def publish_docs(session):
    session.install(*doc_dependencies)
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
