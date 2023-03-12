import subprocess
import sys
from pathlib import Path

import nox  # type: ignore

PYTHON_ALL_VERSIONS = ["3.7", "3.8", "3.9", "3.10", "3.11"]
PYTHON_DEFAULT_VERSION = "3.11"
DOC_DEPENDENCIES = [".", "jinja2", "mkdocs", "mkdocs-material"]
MAN_DEPENDENCIES = [".", "argparse-manpage[setuptools]"]
LINT_DEPENDENCIES = [
    "black==22.8.0",
    "mypy==0.930",
    "packaging>=20.0",
    "ruff==0.0.254",
    "types-jinja2",
]
# Packages whose dependencies need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
PREBUILD_PACKAGES = {"all": ["jupyter==1.0.0"], "macos": [], "unix": [], "win": []}
PIPX_TESTS_CACHE_DIR = Path("./.pipx_tests/package_cache")
PIPX_TESTS_PACKAGE_LIST_DIR = Path("testdata/tests_packages")

# Platform logic
if sys.platform == "darwin":
    PLATFORM = "macos"
elif sys.platform == "win32":
    PLATFORM = "win"
else:
    PLATFORM = "unix"

# Set nox options
if PLATFORM == "win":
    # build_docs fail on Windows, even if `chcp.com 65001` is used
    nox.options.sessions = ["tests", "lint", "build_man"]
else:
    nox.options.sessions = ["tests", "lint", "build_docs", "build_man"]
nox.options.reuse_existing_virtualenvs = True


def prebuild_wheels(session, prebuild_dict):
    prebuild_list = prebuild_dict.get("all", []) + prebuild_dict.get(PLATFORM, [])

    session.install("wheel")
    wheel_dir = Path(session.virtualenv.location) / "prebuild_wheels"
    wheel_dir.mkdir(exist_ok=True)

    for prebuild in prebuild_list:
        session.run("pip", "wheel", f"--wheel-dir={wheel_dir}", prebuild, silent=True)


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


def on_main_no_changes(session):
    if has_changes():
        session.error("All changes must be committed or removed before publishing")
    branch = get_branch()
    if branch != "main":
        session.error(f"Must be on 'main' branch. Currently on {branch!r} branch")


@nox.session(python=PYTHON_ALL_VERSIONS)
def refresh_packages_cache(session):
    """Populate .pipx_tests/package_cache"""
    print("Updating local tests package spec file cache...")
    PIPX_TESTS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
    session.run(
        "python",
        "scripts/update_package_cache.py",
        str(PIPX_TESTS_PACKAGE_LIST_DIR),
        str(PIPX_TESTS_CACHE_DIR),
    )


def tests_with_options(session, net_pypiserver):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    prebuild_wheels(session, PREBUILD_PACKAGES)
    session.install("-e", ".", "pytest", "pytest-cov")
    tests = session.posargs or ["tests"]

    if net_pypiserver:
        pypiserver_option = ["--net-pypiserver"]
    else:
        session.install("pypiserver")
        refresh_packages_cache(session)
        pypiserver_option = []

    session.run("pytest", *pypiserver_option, "--cov=pipx", "--cov-report=", *tests)
    session.notify("cover")


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests_internet(session):
    """Tests using internet pypi only"""
    tests_with_options(session, net_pypiserver=True)


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests(session):
    """Tests using local pypiserver only"""
    tests_with_options(session, net_pypiserver=False)


@nox.session(python=PYTHON_ALL_VERSIONS)
def test_all_packages(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("-e", ".", "pytest")
    tests = session.posargs or ["tests"]
    session.run(
        "pytest",
        "-v",
        "--tb=no",
        "--show-capture=no",
        "--net-pypiserver",
        "--all-packages",
        *tests,
    )


@nox.session
def cover(session):
    """Coverage analysis"""
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def lint(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*LINT_DEPENDENCIES)
    files = [str(Path("src") / "pipx"), "tests", "scripts"] + [
        str(p) for p in Path(".").glob("*.py")
    ]
    session.run("ruff", *files)
    session.run("black", "--check", *files)
    session.run(
        "mypy",
        "--strict-equality",
        "--no-implicit-optional",
        "--warn-unused-ignores",
        *files,
    )


@nox.session(python=PYTHON_ALL_VERSIONS)
def develop(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*DOC_DEPENDENCIES, *LINT_DEPENDENCIES)
    session.install("-e", ".")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("build")
    session.run("rm", "-rf", "dist", "build", external=True)
    session.run("python", "-m", "build")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def publish(session):
    on_main_no_changes(session)
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("twine")
    build(session)
    print("REMINDER: Has the changelog been updated?")
    session.run("python", "-m", "twine", "upload", "dist/*")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_docs(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*DOC_DEPENDENCIES)
    session.env[
        "PIPX__DOC_DEFAULT_PYTHON"
    ] = "typically the python used to execute pipx"
    session.run("python", "scripts/generate_docs.py")
    session.run("mkdocs", "build")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def publish_docs(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*DOC_DEPENDENCIES)
    build_docs(session)
    session.run("mkdocs", "gh-deploy")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def watch_docs(session):
    session.install(*DOC_DEPENDENCIES)
    session.run("mkdocs", "serve")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_man(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*MAN_DEPENDENCIES)
    session.env[
        "PIPX__DOC_DEFAULT_PYTHON"
    ] = "typically the python used to execute pipx"
    session.run("python", "scripts/generate_man.py")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def pre_release(session):
    on_main_no_changes(session)
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("mypy")
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


@nox.session(python=PYTHON_DEFAULT_VERSION)
def post_release(session):
    on_main_no_changes(session)
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install("mypy")
    session.run("python", "scripts/pipx_postrelease.py")
    session.run("git", "--no-pager", "diff", external=True)
    print("")
    session.log(
        "If `git diff` above looks ok, execute the following command:\n\n"
        "    git commit -a -m 'Post-release.'\n"
    )


@nox.session(python=PYTHON_ALL_VERSIONS)
def create_test_package_list(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    output_dir = (
        session.posargs[0] if session.posargs else str(PIPX_TESTS_PACKAGE_LIST_DIR)
    )
    session.run(
        "python",
        "scripts/list_test_packages.py",
        str(PIPX_TESTS_PACKAGE_LIST_DIR / "primary_packages.txt"),
        output_dir,
    )
